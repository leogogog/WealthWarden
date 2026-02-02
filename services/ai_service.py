from google import genai
import os
import json
from datetime import datetime

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Initialize the new Client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash" # Upgrade to latest Flash model for speed/cost or keep user pref

    def analyze_input(self, user_input, image_data=None, mime_type=None):
        """
        Analyzes input to determine intent (RECORD, QUERY, CHAT) and extracts relevant data.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        You are a smart financial assistant. Analyze the user's input (Text or Image).
        Current Date: {current_date}
        
        Determine the INTENT:
        ... (Logic same as before) ...
        Input Text: {user_input}
        """

        try:
            if image_data and mime_type:
                # Create the image content part using the new SDK types
                from google.genai import types
                image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)
                
                # Use a specific prompting strategy for images
                contents = [
                    prompt, 
                    "\nHere is the image of the receipt/transaction:",
                    image_part
                ]
            else:
                contents = prompt
            
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=contents
            )
            
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"Error parsing AI intent: {e}")
            return {"intent": "CHAT", "reply": "I'm having trouble understanding that image/text. Could you try again?"}

    def generate_natural_response(self, user_query, data_summmary):
        """
        Generates a natural language answer based on retrieved data.
        """
        prompt = f"""
        User Question: {user_query}
        
        Database Data:
        {data_summmary}
        
        Task: Answer the user's question naturally using the data provided. 
        If it's a question like "How much did I spend?", give the number and maybe a brief comment.
        If the data is empty or zero, say so politely.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Here is the data: {data_summmary}"

    def get_financial_advice(self, financial_summary):
        """
        Generates advice based on a summary of recent finances.
        """
        prompt = f"""
        You are a highly capable personal finance advisor. 
        Analyze the following financial summary for the current month.
        
        Data:
        {financial_summary}
        
        Please provide a "Scientific Financial Analysis" including:
        1. **Status Check**: Are they saving enough? (Reference the 50/30/20 rule if applicable, though you may not have distinct Need/Want data, infer if possible or just comment on Savings Rate).
        2. **Prediction**: Based on the daily average so far, predict the Total Expense by the end of the month.
        3. **Actionable Advice**: 3 specific, brief tips to improve their financial health.
        
        Keep the tone professional yet encouraging. Use emoji bullets.
        """
        
        try:
            # New SDK Usage
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return "Sorry, I couldn't generate advice right now. " + str(e)

