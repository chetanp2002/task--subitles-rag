import os
from groq import Groq

class LLMService:
    def __init__(self):
        # Get API key from environment or use a default for testing
        api_key = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")
        self.client = Groq(api_key=api_key)
    
    def get_completion(self, prompt: str) -> str:
        """Get completion from Groq LLM"""
        try:
            completion = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful AI assistant specializing in video editing and general questions."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"