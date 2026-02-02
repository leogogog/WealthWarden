---
name: personal-finance
description: Manage personal finances by adding transactions or viewing monthly reports. Use this when the user reports spending or asks for their budget/expenses.
metadata: {"openclaw":{"emoji":"💰"}}
---

# Personal Finance Assistant

Manage the user's personal ledger using the `finance.py` script.
Data is stored locally in `finance_data.json`.

## Usage

### 1. Add Transaction (记账)
Use when the user says "I spent 50 on lunch" or "Bought a book for 20".

```bash
# General format
python3 ~/Desktop/Me/FinanceAssistant/finance.py add --amount <NUM> --category "<STR>" --desc "<STR>"

# Examples
python3 ~/Desktop/Me/FinanceAssistant/finance.py add --amount 35.5 --category "餐饮" --desc "午餐: 麦当劳"
python3 ~/Desktop/Me/FinanceAssistant/finance.py add --amount 120 --category "交通" --desc "打车去机场"
python3 ~/Desktop/Me/FinanceAssistant/finance.py add --amount 299 --category "购物" --desc "优衣库T恤" --date "2023-10-01"
```

### 2. View Report (查账)
Use when the user asks "How much did I spend this month?" or "Show my expenses".

```bash
# Current month
python3 ~/Desktop/Me/FinanceAssistant/finance.py report

# Specific month
python3 ~/Desktop/Me/FinanceAssistant/finance.py report --month "2023-09"
```

## Categories
Common categories to use if not specified:
- 餐饮 (Food/Dining)
- 交通 (Transport)
- 购物 (Shopping)
- 娱乐 (Entertainment)
- 居家 (Home/Utilities)
- 医疗 (Health)
- 其他 (Other)
