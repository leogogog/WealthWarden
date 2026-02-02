import asyncio
import os
from dotenv import load_dotenv
from services.ai_service import AIService

load_dotenv()

async def test():
    print("Initializing AI Service...")
    try:
        service = AIService()
    except Exception as e:
        print(f"Skipping: {e}")
        return

    inputs = [
        "Fund profit 120.5",
        "Stock loss 500",
        "Bitcoin balance is 50000"
    ]
    
    for txt in inputs:
        print(f"\n--- Testing: '{txt}' ---")
        result = await service.analyze_input(txt)
        print("Intent:", result.get("intent"))
        if result.get("transaction_data"):
            print("Transaction:", result.get("transaction_data"))
        if result.get("assets"):
            print("Assets:", result.get("assets"))

if __name__ == "__main__":
    asyncio.run(test())
