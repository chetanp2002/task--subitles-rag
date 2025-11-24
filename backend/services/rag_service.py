import sqlite3
import os

class RAGService:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for conversation storage"""
        conn = sqlite3.connect('conversations.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    
    def store_conversation(self, user_id: str, message: str, response: str):
        """Store conversation in database"""
        conn = sqlite3.connect('conversations.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversations (user_id, message, response)
            VALUES (?, ?, ?)
        ''', (user_id, message, response))
        conn.commit()
        conn.close()
    
    def get_conversation_context(self, user_id: str, current_message: str, limit: int = 3) -> str:
        """Get relevant conversation context"""
        try:
            conn = sqlite3.connect('conversations.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message, response FROM conversations 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            conversations = cursor.fetchall()
            conn.close()
            
            if not conversations:
                return "No previous conversation history."
            
            context_parts = []
            for msg, resp in reversed(conversations):  # Reverse to get chronological order
                context_parts.append(f"User: {msg}\nAssistant: {resp}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            print(f" Error getting conversation context: {e}")
            return "No previous conversation history."