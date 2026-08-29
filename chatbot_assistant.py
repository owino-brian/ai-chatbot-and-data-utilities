import time
import random

class TechnicalSupportChatbot:
    def __init__(self, developer_name):
        self.developer = developer_name
        self.greetings = ["Hello!", "Hi there!", "Greetings! How can I assist you with your tech stack today?"]
        self.responses = {
            "data": "For data workflows, I recommend utilizing Python (Pandas/NumPy) or R (Tidyverse) pipelines.",
            "bot": "This chatbot operates as a rule-based simulation tracking modular responses.",
            "document": "Structured markdown frameworks ensure developer APIs remain highly scannable and accessible.",
            "help": "You can query me about 'data', 'bot', or 'document' mechanics."
        }

    def simulate_conversation(self, query):
        print(f"User Query: '{query}'")
        time.sleep(1) # Simulates system processing latency
        
        normalized_query = query.lower()
        for key in self.responses:
            if key in normalized_query:
                return f"🤖 Chatbot: {self.responses[key]}"
        return "🤖 Chatbot: Intrigued! Let's schedule a dedicated consulting milestone to look over this requirement."

if __name__ == "__main__":
    # Initialize the automated chatbot simulation instance
    assistant = TechnicalSupportChatbot(developer_name="Owino Brian")
    print(f"--- Launching Chatbot Sandbox by {assistant.developer} ---")
    print(random.choice(assistant.greetings))
    
    # Simulating standard production client logs
    queries = ["Tell me about your data cleaning tooling", "How do I build a bot?", "Do you write documentation?"]
    for q in queries:
        print(assistant.simulate_conversation(q))
        print("-" * 30)
