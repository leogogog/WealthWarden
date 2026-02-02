import logging
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from db.database import init_db, get_db
from db.models import Transaction, Asset
from services.ai_service import AIService
from services.analyzer import FinanceAnalyzer

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

ai_service = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access attempt from user_id: {user.id} (Expected: {ALLOWED_USER_ID})")
        return # Silent ignore for unauthorized users
        
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm your Personal Finance Bot. 🤖\n"
        f"Send me any expense, income, or receipt photo, and I'll track it for you."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    await update.message.reply_text(
        "Commands:\n"
        "/start - Init bot\n"
        "/report - Get scientific analysis & prediction\n"
        "Or just send text/photos to log transactions!"
    )

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a financial report and analysis."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    status_msg = await update.message.reply_text("Crunching the numbers... 📊")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        db = next(get_db())
        analyzer = FinanceAnalyzer(db)
        
        # 1. Get Stats
        stats = analyzer.get_monthly_summary()
        summary_text = analyzer.format_summary_text(stats)
        
        if stats['total_income'] == 0 and stats['total_expense'] == 0:
            await status_msg.edit_text("No data found for this month yet! Start logging first.")
            return

        # 2. Get AI Analysis (ASYNC)
        analysis = await ai_service.get_financial_advice(summary_text)
        
        # 3. Format Output
        final_reply = (
            f"📊 *Monthly Report: {stats['period']}*\n\n"
            f"💰 *Income:* {stats['total_income']:.2f}\n"
            f"💸 *Expense:* {stats['total_expense']:.2f}\n"
            f"📉 *Daily Avg:* {stats['daily_average']:.2f}\n"
            f"🏦 *Net:* {stats['net_savings']:.2f}\n\n"
            f"🧠 *AI Analysis & Prediction:*\n"
            f"{analysis}"
        )
        
        await status_msg.edit_text(final_reply, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await status_msg.edit_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages with Smart Intent."""
    if update.effective_user.id != ALLOWED_USER_ID: 
        logger.warning(f"Unauthorized text message from: {update.effective_user.id}")
        return

    text = update.message.text
    # REMOVED: status_msg = await update.message.reply_text("Thinking... 🤔")
    # Instead, use typing action which is non-intrusive
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # 1. Analyze Intent (ASYNC)
        result = await ai_service.analyze_input(text)
        
        # Try to handle as Dual Intent (Transaction + Assets)
        # This covers RECORD, UPDATE_ASSET, and MIXED
        if await handle_dual_intent(update, context, result):
            return

        intent = result.get("intent", "CHAT")
        db = next(get_db())

        # --- CASE 2: QUERY ---
        if intent == "QUERY":
            analyzer = FinanceAnalyzer(db)
            query_type = result.get("query_type")
            
            # Fetch relevant data
            if result.get("specific_category"):
                data_summary = analyzer.get_category_spending(result.get("specific_category"))
            else:
                # Default to monthly summary for general questions
                stats = analyzer.get_monthly_summary()
                data_summary = analyzer.format_summary_text(stats)
            
            # Generate Answer (ASYNC)
            answer = await ai_service.generate_natural_response(text, data_summary)
            await update.message.reply_text(answer)

        # --- CASE 5: DELETE ---
        elif intent == "DELETE":
            target = result.get("target")
            search_term = result.get("search_term")
            
            transaction_to_delete = None
            
            if target == "LAST":
                # Get the absolute last transaction
                transaction_to_delete = db.query(Transaction).order_by(Transaction.id.desc()).first()
                if not transaction_to_delete:
                    await update.message.reply_text("Your transaction history is empty.")
                    return

            elif target == "SEARCH" and search_term:
                # Fuzzy search by description
                candidates = db.query(Transaction).filter(
                    Transaction.description.ilike(f"%{search_term}%")
                ).order_by(Transaction.id.desc()).all()
                
                if len(candidates) == 0:
                    await update.message.reply_text(f"I couldn't find any transaction matching '{search_term}'.")
                    return
                elif len(candidates) == 1:
                    transaction_to_delete = candidates[0]
                else:
                    # Too many matches
                    msg = f"Found {len(candidates)} matches for '{search_term}'. Please be more specific (e.g. mention the amount).\n\n"
                    # List top 3
                    for tx in candidates[:3]:
                        msg += f"- {tx.description} ({tx.amount} {tx.currency})\n"
                    await update.message.reply_text(msg)
                    return
            
            if transaction_to_delete:
                db.delete(transaction_to_delete)
                db.commit()
                await update.message.reply_text(
                    f"🗑️ Deleted: {transaction_to_delete.description} ({transaction_to_delete.amount} {transaction_to_delete.currency})"
                )
            else:
                # Fallback if target is weird or search term missing
                await update.message.reply_text("I'm not sure which transaction you want me to delete.")

        # --- CASE 4: CHAT ---
        else:
            reply = result.get("reply", "I'm here to help you manage your finances!")
            await update.message.reply_text(reply)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos (receipts, etc)."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    status_msg = await update.message.reply_text("Analyzing image... 🖼️")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download headers
        from io import BytesIO
        img_buffer = BytesIO()
        await file.download_to_memory(img_buffer)
        img_bytes = img_buffer.getvalue()
        
        # Determine caption or use default
        user_input = update.message.caption or "Analyze this receipt/image"
        
        # 1. Analyze with AI (Vision) (ASYNC)
        result = await ai_service.analyze_input(user_input, image_data=img_bytes, mime_type="image/jpeg")
        
        # 2. Try to handle as Dual Intent (Transaction + Assets)
        # This covers RECORD, UPDATE_ASSET, and MIXED intents if keys are present
        was_processed = await handle_dual_intent(update, context, result)
        
        if was_processed:
            # If we successfully processed data, remove the "Analyzing..." message or just leave it
            # The handle_dual_intent sends a new reply. We can delete the status msg.
            await status_msg.delete()
            return
            
        # 3. Fallback for QUERY or CHAT
        intent = result.get("intent", "CHAT")
        if intent == "QUERY":
             await status_msg.edit_text(f"I found this data: {result}")
        else:
            reply = result.get("reply", "I saw the image but couldn't extract finance data.")
            await status_msg.edit_text(reply)
            
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await status_msg.edit_text(f"Error analyzing photo: {str(e)}")

def main() -> None:
    """Start the bot."""
    global ai_service
    
    # Initialize DB
    init_db()
    
    # Initialize AI
    default_currency = os.getenv("DEFAULT_CURRENCY", "CNY")
    try:
        ai_service = AIService(currency=default_currency)
    except Exception as e:
        logger.error(f"Failed to init AI Service: {e}")
        return

    # Create the Application
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return
        
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", handle_report))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

def is_duplicate_transaction(db, data):
    """Check if a similar transaction exists within the last 24 hours."""
    from datetime import datetime, timedelta
    
    # Time window: 24 hours (since yields might be reported daily at similar times)
    time_window = datetime.utcnow() - timedelta(hours=24)
    
    exists = db.query(Transaction).filter(
        Transaction.amount == data.get('amount'),
        Transaction.type == data.get('type'),
        # Allow some flexibility or exact match? Exact for now.
        Transaction.category == data.get('category'), 
        Transaction.date >= time_window
    ).first()
    
    return exists is not None

async def handle_dual_intent(update, context, result):
    """
    Handles potential mixed content: both transaction_data and assets.
    Returns True if any financial data was processed, False otherwise.
    """
    db = next(get_db())
    processed_any = False
    response_parts = []
    
    # 1. Process Transaction
    tx_data = result.get("transaction_data")
    if tx_data and tx_data.get("amount"):
        processed_any = True
        
        if is_duplicate_transaction(db, tx_data):
            response_parts.append(f"⚠️ *Skipped Duplicate*: {tx_data.get('type')} {tx_data.get('amount')} (recorded recently)")
        else:
            new_tx = Transaction(
                amount=tx_data.get('amount'),
                currency=tx_data.get('currency', 'CNY'),
                category=tx_data.get('category'),
                type=tx_data.get('type'),
                description=tx_data.get('description'),
                raw_text="[Auto-Detected] " + (update.message.caption or update.message.text or "")
            )
            db.add(new_tx)
            # Commit processing immediately for transaction
            db.commit() 
            
            response_parts.append(
                f"✅ *Recorded {tx_data.get('type')}*\n"
                f"{tx_data.get('category')}: {tx_data.get('amount')} {tx_data.get('currency')}"
            )

    # 2. Process Assets
    assets_data = result.get("assets")
    if assets_data:
        processed_any = True
        asset_summary = await handle_asset_update(db, assets_data)
        response_parts.append(asset_summary)
        
    if processed_any:
        final_response = "\n\n".join(response_parts)
        await update.message.reply_text(final_response, parse_mode='Markdown')
        
    return processed_any

async def handle_asset_update(db, assets_data):
    """Helper to update multiple assets in DB and return summary."""
    updated_names = []
    skipped_names = []
    
    for item in assets_data:
        name = item.get("name")
        balance = item.get("balance")
        if not name or balance is None: continue
        
        asset = db.query(Asset).filter(Asset.name == name).first()
        new_balance = float(balance)
        
        if asset:
            if abs(asset.balance - new_balance) < 0.01:
                skipped_names.append(name)
                continue
            asset.balance = new_balance
            if item.get("category"): asset.category = item.get("category")
            if item.get("currency"): asset.currency = item.get("currency")
        else:
            asset = Asset(
                name=name,
                balance=new_balance,
                category=item.get("category", "OTHERS"),
                currency=item.get("currency", "CNY")
            )
            db.add(asset)
        
        updated_names.append(f"- *{name}*: {new_balance} {asset.currency}")
    
    db.commit()
    
    response = ""
    if updated_names:
        response += "📈 *Assets Updated:*\n" + "\n".join(updated_names) + "\n\n"
    if skipped_names:
        response += "🆗 *Unchanged*: " + ", ".join(skipped_names)
    
    if not response:
        return "No asset data found or all up to date."
        
    return response.strip()

if __name__ == "__main__":
    main()
