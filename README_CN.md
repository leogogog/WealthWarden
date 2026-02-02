# 💰 AI Finance Assistant (AI 财务助手)

[English](./README.md) | **中文**

一个基于 **Gemini 2.0 Flash** 的 Telegram 智能个人财务机器人。
它可以追踪您的支出、收入和收据，并提供科学的财务分析和预测。

![Demo](./assets/demo.png)

## 🚀 功能特点
- **智能记账**: 通过文本（如 "午餐 50元"）或照片（收据）记录支出/收入。
- **财务分析**: 询问 "我在食物上花了多少钱？" 或获取完整的月度报告 `/report`。
- **删除记录**: 只需说 "删除上一条记录" 或 "删除打车费用"。
- **视觉识别**: 支持通过分析收据图片自动录入数据。

## 🛠️ 快速开始

### 前置要求
- Python 3.11+ 或 Docker
- [Telegram Bot Token](https://t.me/BotFather)
- [Google Gemini API Key](https://aistudio.google.com/)

### 1. 环境配置
克隆代码库并创建 `.env` 文件：
```bash
cp .env.example .env
```
编辑 `.env` 并填写您的密钥：
```
TELEGRAM_BOT_TOKEN=您的bot_token
GEMINI_API_KEY=您的gemini_key
ALLOWED_USER_ID=123456789  # 您的 Telegram User ID
```

### 2. 使用 Docker 运行 (推荐)
```bash
docker-compose up -d --build
```

### 3. 手动运行
```bash
# 安装依赖
pip install -r requirements.txt

# 运行机器人
python main.py
```

## 🗑️ 重置数据库
如果需要完全清除所有数据并重新开始：
1. 停止机器人。
2. 删除数据库文件：
   ```bash
   rm instance/finance.db  # 或者 finance.db (取决于您的配置)
   ```
   *(注意：程序将在下次运行时自动创建一个空的数据库。)*

## 📝 使用示例
| 动作 | 指令 / 消息 |
| :--- | :--- |
| **记录支出** | "买了300元的杂货" |
| **记录收入** | "收到工资 5000" |
| **分析收据** | *发送一张收据的照片* |
| **查询消费** | "显示我的餐饮支出" |
| **删除数据** | "删除上一条" |
| **获取报告** | `/report` |
