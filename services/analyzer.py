from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models import Transaction
from datetime import datetime, timedelta

class FinanceAnalyzer:
    def __init__(self, db: Session):
        self.db = db

    def get_monthly_summary(self):
        """
        Aggregates data for the current month.
        """
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Query transactions for this month
        txs = self.db.query(Transaction).filter(
            Transaction.date >= start_of_month
        ).all()
        
        return self._aggr_transactions(txs, now)

    def get_category_spending(self, category_name):
        """
        Get spending for a specific category this month.
        """
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        txs = self.db.query(Transaction).filter(
            Transaction.date >= start_of_month,
            Transaction.category.ilike(f"%{category_name}%"),
            Transaction.type == 'EXPENSE'
        ).all()
        
        total = sum(t.amount for t in txs)
        return f"Total spent on {category_name} this month: {total:.2f}"

    def _aggr_transactions(self, txs, now):
        total_income = 0.0
        total_expense = 0.0
        by_category = {}
        
        for tx in txs:
            amt = tx.amount
            if tx.type == 'INCOME':
                total_income += amt
            elif tx.type == 'EXPENSE':
                total_expense += amt
                cat = tx.category or "Uncategorized"
                by_category[cat] = by_category.get(cat, 0.0) + amt
                
        days_passed = now.day
        daily_avg = total_expense / days_passed if days_passed > 0 else 0
        
        return {
            "period": f"{now.strftime('%B %Y')}",
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": total_income - total_expense,
            "categories": by_category,
            "daily_average": daily_avg
        }
    
    def get_asset_summary(self):
        """
        Retrieves total assets and distribution.
        """
        from db.models import Asset
        assets = self.db.query(Asset).all()
        
        total_balance = sum(a.balance for a in assets)
        by_category = {}
        for a in assets:
            cat = a.category or "OTHERS"
            by_category[cat] = by_category.get(cat, 0.0) + a.balance
            
        return {
            "total_asset_balance": total_balance,
            "asset_distribution": by_category,
            "asset_list": [{"name": a.name, "balance": a.balance, "category": a.category} for a in assets]
        }
    
    def format_summary_text(self, data):
        """Convert stats to a readable string for the AI."""
        if isinstance(data, str): return data # Already text
        
        cat_str = "\n".join([f"- {k}: {v:.2f}" for k, v in data.get('categories', {}).items()])
        
        asset_summary = self.get_asset_summary()
        asset_dist_str = "\n".join([f"- {k}: {v:.2f}" for k, v in asset_summary['asset_distribution'].items()])
        
        return (
            f"--- Financial Summary ---\n"
            f"Period: {data['period']}\n"
            f"Total Income: {data['total_income']:.2f}\n"
            f"Total Expense: {data['total_expense']:.2f}\n"
            f"Net Savings: {data['net_savings']:.2f}\n"
            f"Daily Avg Expense: {data['daily_average']:.2f}\n"
            f"Expense Breakdown:\n{cat_str}\n\n"
            f"--- Asset Distribution ---\n"
            f"Total Asset Balance: {asset_summary['total_asset_balance']:.2f}\n"
            f"Distribution:\n{asset_dist_str}"
        )
