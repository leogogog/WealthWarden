
import os
import sys
from sqlalchemy.orm import Session
from db.database import SessionLocal, init_db
from db.models import Asset
from main import handle_asset_update
import asyncio

async def test_assets():
    print("Testing Asset Management Feature...")
    init_db()
    db = SessionLocal()
    
    # Mock data from AI
    assets_data = [
        {"name": "Alipay", "balance": 5000.50, "category": "SAVINGS", "currency": "CNY"},
        {"name": "Vanguard Fund", "balance": 12000.00, "category": "FUND", "currency": "USD"}
    ]
    
    print("Step 1: Updating assets...")
    summary = await handle_asset_update(db, assets_data)
    print(summary)
    
    # Verify in DB
    alipay = db.query(Asset).filter(Asset.name == "Alipay").first()
    vanguard = db.query(Asset).filter(Asset.name == "Vanguard Fund").first()
    
    if alipay and alipay.balance == 5000.50 and vanguard and vanguard.balance == 12000.00:
        print("SUCCESS: Database updated correctly.")
    else:
        print("FAILURE: Database not updated correctly.")
        db.close()
        return

    print("\nStep 2: Testing Analyzer...")
    from services.analyzer import FinanceAnalyzer
    analyzer = FinanceAnalyzer(db)
    
    asset_summary = analyzer.get_asset_summary()
    print(f"Total Balance: {asset_summary['total_asset_balance']}")
    
    if abs(asset_summary['total_asset_balance'] - 17000.50) < 0.01:
        print("SUCCESS: Analyzer calculated total correctly.")
    else:
        print(f"FAILURE: Analyzer total incorrect. Expected 17000.50, got {asset_summary['total_asset_balance']}")

    db.close()

if __name__ == "__main__":
    asyncio.run(test_assets())
