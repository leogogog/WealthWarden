# WealthWarden AI (财富守卫 AI) 🛡️💰

**WealthWarden** is a secure, private, and intelligent Personal Finance Assistant that lives in your Telegram. Powered by Google's **Gemini 3 Pro**, it turns your natural language messages into structured financial data, provides scientific analysis, and helps you predict future expenses.

**WealthWarden** 是一个安全、通过 Telegram 运行的只能个人财务助手。由 Google **Gemini 3 Pro** 驱动，它能将您的自然语言消息转化为结构化的财务数据，提供科学的财务分析，并帮助您预测未来的支出。

---

## ✨ Features (功能特性)

### 1. Zero-Friction Logging (零摩擦记账) 📝
*   **Natural Language**: Just send "Lunch $15", "Taxi 50 CNY", "Salary 5000".
    *   **自然语言**: 只需发送 "午饭 50", "打车 20", "工资 5000"。
*   **Automatic Parsing**: The AI automatically extracts date, amount, currency, category, and description.
    *   **自动解析**: AI 自动提取日期、金额、货币、类别和描述。

### 2. Scientific Analysis & Prediction (科学分析与预测) 🧠
*   **Command**: `/report`
*   **Real-time Aggregation**: Instantly calculates your Month-to-Date Income, Expense, and Net Savings.
    *   **实时汇总**: 即时计算本月的收入、支出和净储蓄。
*   **50/30/20 Rule Check**: AI evaluates if your spending aligns with healthy financial habits.
    *   **50/30/20 法则检查**: AI 评估您的支出是否符合健康的财务习惯。
*   **Expense Prediction**: Forecasts your end-of-month total based on current burn rate.
    *   **支出预测**: 基于当前的消费速度预测月底的总支出。
*   **Actionable Advice**: Gives you specific, scientific tips to improve your financial health.
    *   **行动建议**: 提供改善财务健康的具体科学建议。

### 3. Investment Tracking (投资追踪) 📈
*   Log investments: "Bought 10 AAPL at 150".
    *   记录投资: "以 150 的价格买入 10 股 AAPL"。
*   Track your portfolio moves securely.

### 4. Privacy First (隐私至上) 🔒
*   **Self-Hosted**: Runs on your own server (e.g., Rocky Linux, Ubuntu).
    *   **私有部署**: 运行在您自己的服务器上。
*   **Single User Mode**: Hardcoded allowlist to ONLY listen to YOU.
    *   **单用户模式**: 硬编码白名单，仅响应您的指令。
*   **Local DB**: Your data lives in a SQLite file on your disk, not in the cloud.
    *   **本地数据库**: 数据存储在本地 SQLite 文件中，安全可控。

---

## 🛠️ Tech Stack (技术栈)
*   **Core**: Python 3.11+
*   **AI Engine**: Google Gemini 2.0 Flash (via `google-genai` SDK)
*   **Database**: SQLite + SQLAlchemy
*   **Platform**: Telegram Bot API
*   **Deployment**: Docker & Docker Compose

---

## 🚀 Quick Start (快速开始)

### Prerequisites (前提条件)
1.  **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather).
2.  **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/).
3.  **Your Telegram ID**: Get from [@userinfobot](https://t.me/userinfobot).

### Installation via Docker (推荐 Docker 安装)

1.  **Clone / Upload Code**:
    ```bash
    git clone https://github.com/your-repo/finance_bot.git
    cd finance_bot
    ```

2.  **Configure Environment**:
    ```bash
    cp .env.example .env
    nano .env
    # Fill in your TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, and ALLOWED_USER_ID
    ```

3.  **Run Service**:
    ```bash
    docker compose up -d
    ```

4.  **Enjoy**:
    Open Telegram and message your bot!
    *   Type `/start` to verify.
    *   Type `/report` to see your AI financial report.

---

## 🔄 Efficient Updates (高效更新)

If you are updating the code on your server, use `rsync` to upload only changed files (excluding data and secrets):

如果您需要更新服务器上的代码，使用 `rsync` 仅上传变动的文件（排除数据和密钥）：

```bash
rsync -avz --exclude 'data' --exclude '.env' --exclude '.git' ./ user@your-server:/path/to/finance_bot
```

---

## 📄 License
MIT License. Open for modification and personal use.
