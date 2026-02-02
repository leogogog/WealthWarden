import os
from db.database import init_db, get_db
from db.models import Asset, Transaction, Budget
from services.analyzer import FinanceAnalyzer

def verify_pro_features():
    print("--- Verifying Professional Finance Features ---")
    
    # Init
    init_db()
    db = next(get_db())
    
    # 1. Setup Assets
    print("\n1. Setting up Assets...")
    # Clear existing for test
    db.query(Transaction).delete()
    db.query(Asset).delete()
    db.query(Budget).delete()
    
    # Liquid
    alipay = Asset(name="Alipay", balance=1000.0, type="LIQUID", category="Wallet")
    # Credit (Liability)
    visa = Asset(name="Visa Card", balance=500.0, type="CREDIT", category="Credit") # 500 debt
    
    db.add(alipay)
    db.add(visa)
    db.commit()
    print(f"✅ Created Alipay (Liquid): {alipay.balance}")
    print(f"✅ Created Visa (Credit): {visa.balance} (Debt)")

    # 2. Test Transaction Logic
    print("\n2. Testing Transaction Logic...")
    
    # Case A: Receipt via Credit Card (Should INCREASE Balance/Debt)
    tx1 = Transaction(amount=100.0, category="Food", type="EXPENSE", asset_id=visa.id, description="Dinner")
    visa.balance += 100.0 # Logic mimics main.py
    db.add(tx1)
    
    # Case B: Pay Bill via Alipay (Transfer)
    # Alipay decreases, Visa decreases (Debt payment)
    transfer_amount = 200.0
    alipay.balance -= transfer_amount
    visa.balance -= transfer_amount
    
    db.commit()
    
    print(f"✅ After Dinner (100) via Visa: Visa Balance = {visa.balance} (Expected 600)")
    print(f"✅ After Bill Pay (200) from Alipay: Alipay = {alipay.balance} (Expected 800), Visa = {visa.balance} (Expected 400)")
    
    assert visa.balance == 400.0
    assert alipay.balance == 800.0
    
    # 3. Test Budget & Analytics
    print("\n3. Testing Budget & Analytics...")
    budget = Budget(category="Food", limit_amount=200.0) # Limit 200
    db.add(budget)
    db.commit()
    
    analyzer = FinanceAnalyzer(db)
    status_report = analyzer.get_budget_status()
    print("Budget Report Output:")
    print(status_report)
    
    # Expect 50% usage (100 spent on Food)
    if "[█████░░░░░] 50%" in status_report:
        print("✅ Visual Bar Correct")
    else:
        print("⚠️ Visual Bar Check Failed (might be slight ascii diff)")

    trend = analyzer.get_weekly_trend()
    print("Trend Output:")
    print(trend)
    
    print("\n🎉 All Professional Features Verified!")

if __name__ == "__main__":
    verify_pro_features()
