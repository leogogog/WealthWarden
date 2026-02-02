import logging
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
    """Send a welcome message and show menu."""
    user = update.effective_user
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"Unauthorized access from {user.id}")
        return
        
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm your Personal Finance Bot.\n"
        f"Send me any expense, income, or receipt photo, and I'll track it for you.",
        reply_markup=get_main_menu()
    )

async def post_init(application: Application) -> None:
    """Register bot commands with Telegram."""
    commands = [
        BotCommand("start", "Init bot and show menu"),
        BotCommand("assets", "Show all asset balances"),
        BotCommand("report", "Get monthly report"),
        BotCommand("add", "Manual record: /add <amount> <cat> <desc>"),
        BotCommand("setbalance", "Set asset balance: /setbalance <asset> <amount>"),
        BotCommand("transfer", "Transfer: /transfer <from> <to> <amount>"),
        BotCommand("help", "Show help message")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered successfully.")

def get_main_menu():
    """Returns a persistent reply keyboard."""
    keyboard = [
        ["Assets", "Report"],
        ["Add Record", "Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    await update.message.reply_text(
        "Commands:\n"
        "/start - Init bot\n"
        "/report - Get scientific analysis & prediction\n"
        "/assets - Show all asset balances\n"
        "/add <amount> <category> <desc> [asset] - Manual record\n"
        "/setbalance <asset> <amount> - Set asset balance\n"
        "/transfer <from> <to> <amount> - Transfer funds\n"
        "Or just send text/photos to log transactions!"
    )

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a financial report and analysis."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    status_msg = await update.message.reply_text("Crunching the numbers...")
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
            f"Monthly Report: {stats['period']}\n\n"
            f"Income: {stats['total_income']:.2f}\n"
            f"Expense: {stats['total_expense']:.2f}\n"
            f"Daily Avg: {stats['daily_average']:.2f}\n"
            f"Net: {stats['net_savings']:.2f}\n\n"
            f"AI Analysis & Prediction:\n"
            f"{analysis}"
        )
        
        await status_msg.edit_text(final_reply, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await status_msg.edit_text(f"Error: {str(e)}")

async def handle_assets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all assets and their balances."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    db = next(get_db())
    assets = db.query(Asset).all()
    
    if not assets:
        await update.message.reply_text("No assets found. Use AI or /setbalance to create one.")
        return
    
    msg = "Current Assets:\n\n"
    total_cny = 0
    
    for asset in assets:
        msg += f"- *{asset.name}*: {asset.balance:.2f} {asset.currency}\n"
        if asset.currency == "CNY":
            total_cny += asset.balance
            
    msg += f"\nTotal (CNY): {total_cny:.2f}"
    
    # Inline keyboard for quick actions
    keyboard = []
    for asset in assets:
        keyboard.append([
            InlineKeyboardButton(f"Update {asset.name}", callback_data=f"upd_{asset.id}"),
            InlineKeyboardButton(f"Transfer from {asset.name}", callback_data=f"tf_{asset.id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    db = next(get_db())
    
    if data.startswith("upd_"):
        asset_id = int(data.split("_")[1])
        asset = db.get(Asset, asset_id)
        if asset:
            await query.message.reply_text(
                f"How much is currently in *{asset.name}*?\n(Reply with a number)",
                parse_mode='Markdown',
                reply_markup=ForceReply(selective=True)
            )
            context.user_data['expect_balance_for'] = asset_id

    elif data.startswith("tf_"):
        asset_id = int(data.split("_")[1])
        asset = db.get(Asset, asset_id)
        if asset:
            await query.message.reply_text(
                f"Transfer from *{asset.name}* to where?\nFormat: `<target_asset> <amount>`",
                parse_mode='Markdown',
                reply_markup=ForceReply(selective=True)
            )
            context.user_data['expect_transfer_from'] = asset_id

async def handle_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manual add transaction: /add <amount> <category> <desc> [asset]"""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /add <amount> <category> <desc> [asset]")
        return
    
    try:
        amount = float(args[0])
        category = args[1]
        desc = args[2]
        asset_name = args[3] if len(args) > 3 else None
        
        db = next(get_db())
        tx_type = "INCOME" if amount > 0 else "EXPENSE"
        abs_amount = abs(amount)
        
        # Link to asset if provided
        asset_id = None
        asset_msg = ""
        if asset_name:
            asset = db.query(Asset).filter(Asset.name.ilike(f"%{asset_name}%")).first()
            if asset:
                asset_id = asset.id
                if tx_type == "EXPENSE":
                    asset.balance -= abs_amount
                else:
                    asset.balance += abs_amount
                asset_msg = f"\n📉 *{asset.name}* balance updated: {asset.balance:.2f}"
        
        new_tx = Transaction(
            amount=abs_amount,
            category=category,
            description=desc,
            type=tx_type,
            asset_id=asset_id,
            raw_text=f"[Manual] {' '.join(args)}"
        )
        db.add(new_tx)
        db.commit()
        
        await update.message.reply_text(
            f"Recorded {tx_type}\n"
            f"{category}: {abs_amount:.2f} CNY\n"
            f"Desc: {desc}{asset_msg}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_setbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set asset balance: /setbalance <asset> <amount> [category]"""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setbalance <asset> <amount> [category]")
        return
    
    try:
        name = args[0]
        amount = float(args[1])
        category = args[2].upper() if len(args) > 2 else "SAVINGS"
        
        db = next(get_db())
        asset = db.query(Asset).filter(Asset.name.ilike(f"%{name}%")).first()
        
        if asset:
            asset.balance = amount
            if len(args) > 2: asset.category = category
        else:
            asset = Asset(name=name, balance=amount, category=category)
            db.add(asset)
            
        db.commit()
        await update.message.reply_text(f"Asset {asset.name} balance set to {amount:.2f} {asset.currency}", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Transfer funds: /transfer <from> <to> <amount>"""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /transfer <from> <to> <amount>")
        return
    
    try:
        from_name = args[0]
        to_name = args[1]
        amount = float(args[2])
        
        db = next(get_db())
        from_asset = db.query(Asset).filter(Asset.name.ilike(f"%{from_name}%")).first()
        to_asset = db.query(Asset).filter(Asset.name.ilike(f"%{to_name}%")).first()
        
        if not from_asset or not to_asset:
            await update.message.reply_text("Error: One or both asset accounts not found.")
            return
            
        from_asset.balance -= amount
        to_asset.balance += amount
        
        # Record as two transactions or a special TRANSFER type?
        # For simplicity, just record a description
        tx_from = Transaction(
            amount=amount, category="TRANSFER", type="EXPENSE", 
            description=f"Transfer to {to_asset.name}", asset_id=from_asset.id,
            raw_text=f"Transfer {amount} from {from_asset.name} to {to_asset.name}"
        )
        tx_to = Transaction(
            amount=amount, category="TRANSFER", type="INCOME", 
            description=f"Transfer from {from_asset.name}", asset_id=to_asset.id,
            raw_text=f"Transfer {amount} from {from_asset.name} to {to_asset.name}"
        )
        db.add(tx_from)
        db.add(tx_to)
        
        db.commit()
        await update.message.reply_text(
            f"Transfer Complete\n"
            f"From: {from_asset.name} ({from_asset.balance:.2f})\n"
            f"To: {to_asset.name} ({to_asset.balance:.2f})",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages with Smart Intent."""
    if update.effective_user.id != ALLOWED_USER_ID: 
        logger.warning(f"Unauthorized text message from: {update.effective_user.id}")
        return

    text = update.message.text
    
    # Check for ForceReply responses
    if update.message.reply_to_message and update.message.reply_to_message.text:
        reply_to_text = update.message.reply_to_message.text
        db = next(get_db())

        # Case 1: Updating Balance
        if "expect_balance_for" in context.user_data:
            try:
                asset_id = context.user_data.pop('expect_balance_for')
                new_balance = float(text)
                asset = db.get(Asset, asset_id)
                if asset:
                    asset.balance = new_balance
                    db.commit()
                    await update.message.reply_text(f"Asset {asset.name} balance updated to {new_balance:.2f}", parse_mode='Markdown')
                    return
            except ValueError:
                await update.message.reply_text("Please enter a valid number.")
                return

        # Case 2: Transferring
        if "expect_transfer_from" in context.user_data:
            try:
                from_id = context.user_data.pop('expect_transfer_from')
                parts = text.split()
                if len(parts) < 2:
                    await update.message.reply_text("Invalid format. Use: `<to_asset> <amount>`")
                    return
                
                target_name = parts[0]
                amount = float(parts[1])
                
                from_asset = db.get(Asset, from_id)
                to_asset = db.query(Asset).filter(Asset.name.ilike(f"%{target_name}%")).first()
                
                if from_asset and to_asset:
                    from_asset.balance -= amount
                    to_asset.balance += amount
                    db.commit()
                    await update.message.reply_text(
                        f"Transferred {amount} from {from_asset.name} to {to_asset.name}.\n"
                        f"New balances: {from_asset.name}: {from_asset.balance:.2f}, {to_asset.name}: {to_asset.balance:.2f}"
                    )
                    return
                else:
                    await update.message.reply_text("Target asset not found.")
                    return
            except ValueError:
                await update.message.reply_text("Invalid amount.")
                return

    # Handle Main Menu Buttons
    if text == "Assets":
        await handle_assets_command(update, context)
        return
    elif text == "Report":
        await handle_report(update, context)
        return
    elif text == "Add Record":
        await update.message.reply_text("Just send me a message like 'Lunch 50' or 'Payday 5000 via Alipay'")
        return
    elif text == "Help":
        await help_command(update, context)
        return

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
    
    status_msg = await update.message.reply_text("Analyzing image...")
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
        
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("report", handle_report))
    application.add_handler(CommandHandler("assets", handle_assets_command))
    application.add_handler(CommandHandler("add", handle_add_command))
    application.add_handler(CommandHandler("setbalance", handle_setbalance_command))
    application.add_handler(CommandHandler("transfer", handle_transfer_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
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
            response_parts.append(f"Skipped Duplicate: {tx_data.get('type')} {tx_data.get('amount')} (recorded recently)")
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
                f"Recorded {tx_data.get('type')}\n"
                f"{tx_data.get('category')}: {tx_data.get('amount')} {tx_data.get('currency')}"
            )
            
            # 3. Handle Asset Link and Balance Update
            asset_name = tx_data.get("asset_name")
            if asset_name:
                asset = db.query(Asset).filter(Asset.name.ilike(f"%{asset_name}%")).first()
                if asset:
                    new_tx.asset_id = asset.id
                    # Update balance
                    if tx_data.get('type') == 'EXPENSE':
                        asset.balance -= tx_data.get('amount')
                    elif tx_data.get('type') == 'INCOME':
                        asset.balance += tx_data.get('amount')
                    
                    response_parts.append(f"Asset {asset.name} balance updated: {asset.balance:.2f} {asset.currency}")
                else:
                    response_parts.append(f"Asset {asset_name} not found. Balance not updated.")

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
        
        updated_names.append(f"- {name}: {new_balance} {asset.currency}")
    
    db.commit()
    
    response = ""
    if updated_names:
        response += "Assets Updated:\n" + "\n".join(updated_names) + "\n\n"
    if skipped_names:
        response += "Unchanged: " + ", ".join(skipped_names)
    
    if not response:
        return "No asset data found or all up to date."
        
    return response.strip()

if __name__ == "__main__":
    main()
