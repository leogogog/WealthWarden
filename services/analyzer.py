from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models import Transaction, Budget
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
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
        
        return {
            "period": f"{now.strftime('%B %Y')}",
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": net_savings,
            "savings_rate": savings_rate, 
            "categories": by_category,
            "daily_average": daily_avg
        }

    def get_budget_status(self):
        """
        Calculates budget usage for all defined categories.
        Returns a list of formatted strings with progress bars.
        """
        budgets = self.db.query(Budget).all()
        if not budgets:
            return "No budgets set. Use /budget to configure."

        report = "Budget Status\n\n"
        
        # Get monthly usage by category
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage_by_cat = {}
        txs = self.db.query(Transaction).filter(
            Transaction.date >= start_of_month,
            Transaction.type == 'EXPENSE'
        ).all()
        
        for tx in txs:
            if tx.category:
                usage_by_cat[tx.category] = usage_by_cat.get(tx.category, 0.0) + tx.amount

        for b in budgets:
            spent = usage_by_cat.get(b.category, 0.0)
            limit = b.limit_amount
            percent = (spent / limit) * 100 if limit > 0 else 100
            bar = self._generate_progress_bar(spent, limit)
            
            report += f"{b.category}: {spent:.0f}/{limit:.0f}\n"
            report += f"{bar} {percent:.0f}%\n"
            
            if percent >= (b.alert_threshold * 100):
                report += f"Alert: {percent:.0f}% used!\n"
            report += "\n"
            
        return report

    def _generate_progress_bar(self, current, total, length=10):
        if total == 0: return "[:(]" 
        filled = int((current / total) * length)
        filled = min(filled, length) # Cap at 100% for bar
        empty = length - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def get_weekly_trend(self):
        """
        Compares spending of last 7 days vs previous 7 days.
        """
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        prev_7_days = last_7_days - timedelta(days=7)
        
        # Spending Last 7 Days
        txs_current = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= last_7_days,
            Transaction.type == 'EXPENSE'
        ).scalar() or 0.0
        
        # Spending Previous 7 Days
        txs_prev = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= prev_7_days,
            Transaction.date < last_7_days,
            Transaction.type == 'EXPENSE'
        ).scalar() or 0.0
        
        if txs_prev == 0:
            trend_str = "N/A (No previous data)"
        else:
            diff = txs_current - txs_prev
            percent_change = (diff / txs_prev) * 100
            trend_str = f"{abs(percent_change):.1f}% {'up' if diff > 0 else 'down'}"
            
        return (
            f"Weekly Trend (Last 7 Days)\n"
            f"This Week: {txs_current:.2f}\n"
            f"Last Week: {txs_prev:.2f}\n"
            f"Trend: {trend_str}"
        )
    
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
            f"Savings Rate: {data.get('savings_rate', 0):.1f}%\n"
            f"Daily Avg Expense: {data['daily_average']:.2f}\n"
            f"Expense Breakdown:\n{cat_str}\n\n"
            f"--- Asset Distribution ---\n"
            f"Total Asset Balance: {asset_summary['total_asset_balance']:.2f}\n"
            f"Distribution:\n{asset_dist_str}"
        )
