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
        Do not use any emojis in your response.
        Current Date: {current_date}
        
        Determine the INTENT (Can be MIXED):
        1. "RECORD": User wants to track a specific expense or income (e.g. "+1.34 Yesterday's Yield").
        2. "UPDATE_ASSET": User wants to update asset balances.
        3. "QUERY" / "DELETE" / "CHAT": Standard actions.
        
        SPECIAL RULES FOR IMAGES (WEALTH DASHBOARDS):
        - **DUAL EXTRACTION**: Many finance apps show "Today's Profit" (Income) and "Total Assets" (Balance) on the same screen. Extract BOTH if visible.
        - **INTERPRET CONTEXT**: 
            - Green/Red numbers with "+" or "-" usually indicate Income/Expense (Profit/Loss). Treat positive yields as **INCOME**.
            - Large numbers labeled "Assets", "Balance", "Net Worth" are **ASSET** updates.
        - **CATEGORY MAPPING**: Infer the category based on the text (e.g., "Funds" -> FUND, "Wallet" -> CASH, "Stock" -> STOCK). Do not rely on hardcoded lists.
        
        OUTPUT_FORMAT (JSON ONLY):
        Return a single JSON object. Keys `transaction_data` and `assets` can coexist.
        
        {{
            "intent": "MIXED",  // Use "MIXED" if both data types exist, otherwise "RECORD", "UPDATE_ASSET", etc.
            
            // OPTIONAL: If an expense/income is found. 
            // IMPORTANT: Leave "asset_name" null if the payment source is not explicitly clear.
            "transaction_data": {{
                "amount": <float>,
                "currency": "<string, default {self.currency}>",
                "category": "<string, e.g. Investment Yield, Food>",
                "type": "<EXPENSE or INCOME>",
                "description": "<string, e.g. Alipay Yield>",
                "asset_name": "<string, e.g. Alipay, WeChat, ICBC, Optional>"
            }},
            
            // OPTIONAL: If asset balances are found
            "assets": [
                {{
                    "name": "<string>",
                    "balance": <float>,
                    "category": "<SAVINGS, FUND, STOCK, CRYPTO, OTHERS>",
                    "currency": "<string>"
                }}
            ],
            
            // OPTIONAL: For generic chat or queries
            "reply": "<string>",
            "query_type": "..."
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
        Do not use any emojis in your response.
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
        You are the user's Personal Chief Financial Officer (CFO).
        Analyze the following financial summary for the current month.
        
        Data:
        {financial_summary}
        
        Please provide a professional, insight-driven analysis including:
        
        1.  **Health Check & KPIs**:
            *   **Savings Rate**: (Net / Income). Target > 20%.
            *   **Liquid Coverage**: (Total Liquid Assets / Monthly Expense). How many months of runway do they have? (Target > 6 mo).
            *   **Debt Status**: (Total Debt). Is it manageable vs Liquid Assets?
            
        2.  **Forecast**: Based on daily average, predict Month-End Total Expense.
        
        3.  **Proactive Strategy**:
            *   Identify the largest expense category and suggest a specific % reduction target.
            *   If Debt is high, suggest a repayment priority.
            *   If Cash is high (>12 months runway), suggest investing more.
        
        Tone: Professional, direct, analytical. No emojis.
        Structure: Use bullet points.
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

