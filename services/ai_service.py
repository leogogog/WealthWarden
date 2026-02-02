from google import genai
import os
import json
import asyncio
from datetime import datetime

class AIService:
    def __init__(self, currency="CNY"):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.currency = currency
        # Initialize the new Client
        self.client = genai.Client(api_key=self.api_key)
        # Switch to Gemini 2.0 Flash for speed and efficiency
        self.model_name = "gemini-2.0-flash" 

    async def analyze_input(self, user_input, image_data=None, mime_type=None):
        """
        Analyzes input to determine intent (RECORD, QUERY, CHAT) and extracts relevant data.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        You are a smart financial assistant. Analyze the user's input (Text or Image).
        Current Date: {current_date}
        
        Determine the INTENT:
        1. "RECORD": User wants to track an expense or income (e.g., "Lunch 50", "Taxi $20", receipt photo).
        2. "QUERY": User wants to know about their spending (e.g., "How much did I spend on food?", "Status report").
        3. "DELETE": User wants to remove a transaction (e.g., "Delete the last one", "Remove the taxi expense").
        4. "UPDATE_ASSET": User wants to update their asset balances (e.g., "Set Alipay to 5000", or a screenshot of asset distribution).
        5. "CHAT": General conversation or unclear input.

        OUTPUT_FORMAT (JSON ONLY):
        
        CASE 1: RECORD
        {{
            "intent": "RECORD",
            "transaction_data": {{
                "amount": <float>,
                "currency": "<string, default {self.currency}>",
                "category": "<string, e.g., Food, Transport, Salary, Shopping, Others>",
                "type": "<EXPENSE or INCOME>",
                "description": "<string, brief description>"
            }}
        }}

        CASE 2: QUERY
        {{
            "intent": "QUERY",
            "query_type": "<SPENDING_SUMMARY or SPECIFIC_CATEGORY>",
            "specific_category": "<string or null>",
            "time_period": "<string, e.g., this_month>"
        }}

        CASE 3: DELETE
        {{
            "intent": "DELETE",
            "target": "<LAST or SEARCH>",
            "search_term": "<string, keywords to find the record, or null>"
        }}

        CASE 4: UPDATE_ASSET
        {{
            "intent": "UPDATE_ASSET",
            "assets": [
                {{
                    "name": "<string, e.g., Alipay, ICBC Savings, Vanguard Fund>",
                    "balance": <float>,
                    "category": "<SAVINGS, FUND, FIXED_TERM, STOCK, CRYPTO, or OTHERS>",
                    "currency": "<string, default {self.currency}>"
                }}
            ]
        }}

        CASE 5: CHAT
        {{
            "intent": "CHAT",
            "reply": "<string, helpful response>"
        }}
        
        Input Text: {user_input}
        """

        try:
            from google.genai import types
            
            if image_data and mime_type:
                # Create the image content part using the new SDK types
                image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)
                
                # Use a specific prompting strategy for images
                contents = [
                    prompt, 
                    "\nHere is the image of the receipt/transaction:",
                    image_part
                ]
            else:
                contents = prompt
            
            # Execute in thread to prevent blocking the event loop
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name, 
                contents=contents,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            
            # With response_mime_type='application/json', the text is guaranteed to be JSON
            return json.loads(response.text)
        except Exception as e:
            print(f"Error parsing AI intent: {e}")
            return {"intent": "CHAT", "reply": f"Error analyzing input: {str(e)}"}

    async def generate_natural_response(self, user_query, data_summmary):
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
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Here is the data: {data_summmary}"

    async def get_financial_advice(self, financial_summary):
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
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return "Sorry, I couldn't generate advice right now. " + str(e)

