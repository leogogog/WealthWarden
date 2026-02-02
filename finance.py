#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from collections import defaultdict

DATA_FILE = "finance_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_transaction(amount, category, description, date=None):
    data = load_data()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    record = {
        "id": len(data) + 1,
        "date": date,
        "amount": float(amount),
        "category": category,
        "description": description,
        "timestamp": datetime.now().isoformat()
    }
    data.append(record)
    save_data(data)
    print(f"✅ 已记录: [{date}] {category} - {description}: ¥{amount:.2f}")

def show_report(month=None):
    data = load_data()
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    filtered = [d for d in data if d['date'].startswith(month)]
    
    if not filtered:
        print(f"📅 {month} 没有消费记录。")
        return

    total = sum(d['amount'] for d in filtered)
    by_category = defaultdict(float)
    for d in filtered:
        by_category[d['category']] += d['amount']
    
    print(f"\n📊 财务报表 ({month})")
    print("=" * 30)
    print(f"💰 总支出: ¥{total:.2f}")
    print("-" * 30)
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    for cat, amt in sorted_cats:
        percentage = (amt / total) * 100
        bar = "█" * int(percentage / 5)
        print(f"{cat:<10} ¥{amt:>8.2f} ({percentage:>4.1f}%) {bar}")
    print("=" * 30)

def main():
    parser = argparse.ArgumentParser(description="个人财务助理")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add command
    add_parser = subparsers.add_parser("add", help="添加新消费")
    add_parser.add_argument("--amount", "-a", type=float, required=True, help="金额")
    add_parser.add_argument("--category", "-c", type=str, required=True, help="分类 (如: 餐饮, 交通)")
    add_parser.add_argument("--desc", "-d", type=str, required=True, help="描述")
    add_parser.add_argument("--date", type=str, help="日期 YYYY-MM-DD (默认今天)")

    # Report command
    report_parser = subparsers.add_parser("report", help="查看报表")
    report_parser.add_argument("--month", "-m", type=str, help="月份 YYYY-MM")

    args = parser.parse_args()

    if args.command == "add":
        add_transaction(args.amount, args.category, args.desc, args.date)
    elif args.command == "report":
        show_report(args.month)

if __name__ == "__main__":
    main()
