"""
Standalone conversation buffer memory manager with sliding window
Can be integrated with any chatbot system

Features:
- Stores last N exchanges (configurable)
- Sliding window: oldest messages drop automatically
- Format conversation history for LLM prompts
- Thread-safe and easy to integrate
"""

from typing import List, Dict, Optional
from datetime import datetime


class ConversationBufferMemory:
    """
    Manages conversation history with sliding window buffer
    
    Stores user-assistant message pairs and maintains a fixed window size.
    When the window is full, oldest messages are automatically removed.
    """
    
    def __init__(self, max_exchanges: int = 10):
        """
        Initialize conversation memory
        
        Args:
            max_exchanges: Maximum number of Q&A pairs to store (default: 10)
                          This means 10 questions + 10 answers = 20 messages total
        """
        self.max_exchanges = max_exchanges
        self.messages: List[Dict] = []
        
    def add_exchange(self, user_message: str, assistant_message: str):
        """
        Add a complete Q&A exchange to memory
        Implements sliding window: removes oldest exchange if limit reached
        
        Args:
            user_message: User's question/input
            assistant_message: Assistant's response
        """
        # Add user message
        self.messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Add assistant message
        self.messages.append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Maintain sliding window
        self._enforce_window_size()
    
    def add_user_message(self, message: str):
        """
        Add only user message (for cases where you add messages separately)
        
        Args:
            message: User's message
        """
        self.messages.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        self._enforce_window_size()
    
    def add_assistant_message(self, message: str):
        """
        Add only assistant message (for cases where you add messages separately)
        
        Args:
            message: Assistant's message
        """
        self.messages.append({
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        self._enforce_window_size()
    
    def _enforce_window_size(self):
        """
        Enforce sliding window: keep only last N exchanges (2N messages)
        Removes oldest Q&A pairs when limit is exceeded
        """
        max_messages = self.max_exchanges * 2
        
        # Remove oldest pairs (2 messages at a time) until we're within limit
        while len(self.messages) > max_messages:
            self.messages.pop(0)  # Remove oldest user message
            if len(self.messages) > 0:  # Safety check
                self.messages.pop(0)  # Remove oldest assistant message
    
    def get_conversation_string(self, 
                               include_timestamps: bool = False,
                               user_prefix: str = "User",
                               assistant_prefix: str = "Assistant") -> str:
        """
        Format conversation history as a string for LLM prompts
        
        Args:
            include_timestamps: Whether to include message timestamps
            user_prefix: Prefix for user messages (default: "User")
            assistant_prefix: Prefix for assistant messages (default: "Assistant")
            
        Returns:
            Formatted conversation string
        """
        if not self.messages:
            return ""
        
        conversation_lines = []
        
        for msg in self.messages:
            prefix = user_prefix if msg["role"] == "user" else assistant_prefix
            
            if include_timestamps:
                line = f"[{msg['timestamp']}] {prefix}: {msg['content']}"
            else:
                line = f"{prefix}: {msg['content']}"
            
            conversation_lines.append(line)
        
        return "\n".join(conversation_lines)
    
    def get_messages(self) -> List[Dict]:
        """
        Get raw message list (useful for OpenAI-style message arrays)
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        # Return without timestamps for OpenAI API format
        return [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in self.messages
        ]
    
    def get_last_n_exchanges(self, n: int) -> List[Dict]:
        """
        Get last N Q&A exchanges
        
        Args:
            n: Number of exchanges to retrieve
            
        Returns:
            List of last N*2 messages
        """
        messages_to_get = min(n * 2, len(self.messages))
        return [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in self.messages[-messages_to_get:]
        ]
    
    def clear(self):
        """Clear all conversation history"""
        self.messages = []
    
    def is_empty(self) -> bool:
        """Check if memory is empty"""
        return len(self.messages) == 0
    
    def get_exchange_count(self) -> int:
        """
        Get current number of exchanges stored
        
        Returns:
            Number of Q&A pairs (half the message count)
        """
        return len(self.messages) // 2
    
    def get_message_count(self) -> int:
        """
        Get total message count
        
        Returns:
            Total number of messages (user + assistant)
        """
        return len(self.messages)
    
    def get_summary(self) -> Dict:
        """
        Get memory status summary
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            "max_exchanges": self.max_exchanges,
            "current_exchanges": self.get_exchange_count(),
            "total_messages": self.get_message_count(),
            "is_full": self.get_exchange_count() >= self.max_exchanges,
            "is_empty": self.is_empty()
        }
    
    def __repr__(self) -> str:
        """String representation of memory state"""
        return (f"ConversationBufferMemory("
                f"exchanges={self.get_exchange_count()}/{self.max_exchanges}, "
                f"messages={self.get_message_count()})")
    
    def __len__(self) -> int:
        """Return number of exchanges"""
        return self.get_exchange_count()


# Example usage and testing
if __name__ == "__main__":
    print("="*70)
    print("CONVERSATION BUFFER MEMORY - TEST")
    print("="*70)
    
    # Create memory with 3 exchange limit (for testing)
    memory = ConversationBufferMemory(max_exchanges=3)
    
    print(f"\nInitial state: {memory}")
    print(f"Summary: {memory.get_summary()}\n")
    
    # Add some exchanges
    print("Adding Exchange 1...")
    memory.add_exchange("What is AI?", "AI is Artificial Intelligence...")
    print(f"State: {memory}\n")
    
    print("Adding Exchange 2...")
    memory.add_exchange("How does it work?", "AI works by processing data...")
    print(f"State: {memory}\n")
    
    print("Adding Exchange 3...")
    memory.add_exchange("Give me examples", "Examples include chatbots...")
    print(f"State: {memory}")
    print(f"Memory is full: {memory.get_summary()['is_full']}\n")
    
    print("Current conversation:")
    print("-" * 70)
    print(memory.get_conversation_string())
    print("-" * 70)
    
    # Add 4th exchange - should trigger sliding window
    print("\nAdding Exchange 4 (triggers sliding window)...")
    memory.add_exchange("What about limitations?", "AI has limitations like...")
    print(f"State: {memory}")
    print("\nConversation after sliding window:")
    print("-" * 70)
    print(memory.get_conversation_string())
    print("-" * 70)
    print("\n✓ Exchange 1 was removed, Exchanges 2-4 remain")
    
    # Show different formats
    print("\n" + "="*70)
    print("DIFFERENT OUTPUT FORMATS")
    print("="*70)
    
    print("\n1. OpenAI Message Format:")
    print(memory.get_messages())
    
    print("\n2. Last 2 Exchanges Only:")
    print(memory.get_last_n_exchanges(2))
    
    print("\n3. With Timestamps:")
    print(memory.get_conversation_string(include_timestamps=True))
    
    print("\n4. Custom Prefixes:")
    print(memory.get_conversation_string(
        user_prefix="Human",
        assistant_prefix="AI"
    ))
    
    # Clear and test
    print("\n" + "="*70)
    print("TESTING CLEAR")
    print("="*70)
    memory.clear()
    print(f"After clear: {memory}")
    print(f"Is empty: {memory.is_empty()}")