# 💰 AI Finance Assistant

**English** | [中文](./README_CN.md)

A smart personal finance bot for Telegram, powered by **Gemini 2.0 Flash**. 
It tracks your expenses, income, and receipts, providing scientific financial analysis and predictions.

![Demo](./assets/demo.png)

## 🚀 Features
- **Smart Tracking**: Log expenses/income via text ("Lunch $50") or photo (receipts).
- **Analysis**: Ask "How much did I spend on food?" or get a full monthly `/report`.
- **Delete Records**: Just say "Delete the last transaction" or "Delete the taxi expense".
- **Asset Management**: Track and update account balances (Alipay, Bank, Funds) via text or screenshots.
- **Visuals**: Supports analyzing receipt images and asset distribution screenshots.

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+ or Docker
- A [Telegram Bot Token](https://t.me/BotFather)
- A [Google Gemini API Key](https://aistudio.google.com/)

### 1. Setup Environment
Clone the repo and create a `.env` file:
```bash
cp .env.example .env
```
Edit `.env` and fill in your keys:
```
TELEGRAM_BOT_TOKEN=your_token_here
GEMINI_API_KEY=your_gemini_key_here
ALLOWED_USER_ID=123456789  # Your Telegram User ID
DEFAULT_CURRENCY=CNY       # Default currency (CNY, USD, EUR, etc.)
```

### 2. Run with Docker (Recommended)
```bash
docker-compose up -d --build
```

### 3. Run Manually
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

## 🗑️ Reset Database
To completely wipe all data and start fresh:
1. Stop the bot.
2. Delete the database file:
   ```bash
   rm instance/finance.db  # or just finance.db depending on your config
   ```
   *(Note: The app will automatically recreate an empty database on the next run.)*

## 📝 Usage Examples
| Action | Command / Message |
| :--- | :--- |
| **Log Expense** | "Spent 300 on groceries" |
| **Log Income** | "Received $5000 salary" |
| **Analyze Receipt** | *Send a photo of a receipt* |
| **Check Spending** | "Show my food expenses" |
| **Delete Data** | "Delete the last one" |
| **Get Report** | `/report` |
