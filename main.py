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
        BotCommand("wallet", "Manage assets & liabilities"),
        BotCommand("report", "Get monthly report"),
        BotCommand("add", "Manual record: /add <amount> <cat> <desc>"),
        BotCommand("setbalance", "Set asset balance: /setbalance <asset> <amount>"),
        BotCommand("setbalance", "Set asset balance: /setbalance <asset> <amount>"),
        BotCommand("transfer", "Transfer: /transfer <from> <to> <amount>"),
        BotCommand("log", "Log transaction (Guided)"),
        BotCommand("history", "View last 10 transactions"),
        BotCommand("export", "Export data to CSV"),
        BotCommand("help", "Show help message")
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered successfully.")

def get_main_menu():
    """Returns a persistent reply keyboard."""
    keyboard = [
        ["Wallet", "Log Transaction"],
        ["Budget", "Analytics"],
        ["History", "More"]
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

        # 2. Get Weekly Trend
        trend = analyzer.get_weekly_trend()
        
        # 3. Get AI Analysis (ASYNC)
        analysis = await ai_service.get_financial_advice(summary_text)
        
        # 4. Format Output
        final_reply = (
            f"Monthly Report: {stats['period']}\n\n"
            f"Income: {stats['total_income']:.2f}\n"
            f"Expense: {stats['total_expense']:.2f}\n"
            f"Daily Avg: {stats['daily_average']:.2f}\n"
            f"Net: {stats['net_savings']:.2f}\n\n"
            f"{trend}\n\n"
            f"AI Analysis & Prediction:\n"
            f"{analysis}"
        )
        
        await status_msg.edit_text(final_reply, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        await status_msg.edit_text(f"Error: {str(e)}")

async def handle_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advanced Asset View: Assets vs Liabilities, Net Worth."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    db = next(get_db())
    assets = db.query(Asset).all()
    
    if not assets:
        await update.message.reply_text("No assets found. Use /setbalance to create one (e.g. '/setbalance Alipay 500 LIQUID')")
        return

    liquid_assets = []
    credit_liabilities = []
    investments = []
    
    total_liquid = 0.0
    total_debt = 0.0
    total_invest = 0.0
    
    for asset in assets:
        if asset.type == 'CREDIT':
            credit_liabilities.append(asset)
            total_debt += asset.balance # For Credit Cards, balance is usually positive debt
        elif asset.type == 'INVESTMENT':
            investments.append(asset)
            total_invest += asset.balance
        else: # LIQUID or OTHERS
            liquid_assets.append(asset)
            total_liquid += asset.balance

    # Net Worth = (Liquid + Invest) - Debt
    net_worth = (total_liquid + total_invest) - total_debt
    
    msg = "Wallet Overview\n\n"
    
    if liquid_assets:
        msg += "*Liquid Assets:*\n"
        for a in liquid_assets:
            msg += f"- {a.name}: {a.balance:,.2f}\n"
        msg += f"Total: {total_liquid:,.2f}\n\n"
        
    if investments:
        msg += "*Investments:*\n"
        for a in investments:
            msg += f"- {a.name}: {a.balance:,.2f}\n"
        msg += f"Total: {total_invest:,.2f}\n\n"
        
    if credit_liabilities:
        msg += "*Liabilities (Credit Cards):*\n"
        for a in credit_liabilities:
            msg += f"- {a.name}: {a.balance:,.2f}\n"
        msg += f"Total Debt: {total_debt:,.2f}\n\n"
    
    msg += "------------------------\n"
    msg += f"Net Worth: {net_worth:,.2f} {assets[0].currency if assets else 'CNY'}\n"

    # Inline Keyboard
    keyboard = []
    # Add row for common actions
    keyboard.append([InlineKeyboardButton("Transfer / Pay Bill", callback_data="btn_transfer")])
    
    for asset in assets:
        keyboard.append([
             InlineKeyboardButton(f"Manage {asset.name}", callback_data=f"upd_{asset.id}")
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

    elif data == "btn_transfer":
        await query.message.reply_text(
             "Transfer from where to where?\nFormat: `/transfer <from> <to> <amount>`",
             parse_mode='Markdown'
        )

    elif data.startswith("sel_src_"):
        # Source Selected for Log Flow
        asset_id = int(data.split("_")[2])
        tx_data = context.user_data.get('log_data')
        
        if not tx_data:
            await query.message.edit_text("Transaction session expired. Please start over.")
            return

        db = next(get_db())
        asset = db.get(Asset, asset_id)
        
        if asset:
            amount = tx_data['amount']
            category = tx_data['category']
            desc = tx_data['desc']
            
            # Logic: 
            # If Asset Type is CREDIT -> Expense adds to balance (Debt goes up)
            # If Asset Type is LIQUID -> Expense removes from balance
            # Income is reverse
            
            # Standardizing: Expense is always negative in net worth context, 
            # but for Credit Card tracking, we usually want positive balance = debt.
            # Let's stick to the plan:
            # Credit Card: Expenses increase balance.
            # Liquid: Expenses decrease balance.
            
            if tx_data['type'] == 'EXPENSE':
                if asset.type == 'CREDIT':
                    asset.balance += amount
                else:
                    asset.balance -= amount
            else: # INCOME
                 if asset.type == 'CREDIT':
                    asset.balance -= amount # Refund/Payment reduces debt
                 else:
                    asset.balance += amount

            new_tx = Transaction(
                amount=amount,
                category=category,
                description=desc,
                type=tx_data['type'],
                asset_id=asset.id,
                raw_text=f"[Guided] {amount} {category} via {asset.name}"
            )
            db.add(new_tx)
            db.commit()
            
            await query.message.edit_text(
                f"Recorded {tx_data['type']}\n"
                f"{category}: {amount:.2f}\n"
                f"Via: {asset.name} ({asset.type})\n"
                f"New Balance: {asset.balance:.2f}"
            )
            # Clear state
            context.user_data.pop('log_data', None)
        else:
             await query.message.edit_text("Asset not found.")

    elif data.startswith("tf_"):
        # Deprecated logic, supporting just in case
        await query.message.reply_text("Please use /transfer command.")

    elif data.startswith("del_"):
        # 1. Ask for confirmation
        tx_id = data.split("_")[1]
        keyboard = [
            [
                InlineKeyboardButton("Yes, Delete", callback_data=f"cfm_del_{tx_id}"),
                InlineKeyboardButton("Cancel", callback_data="cancel_del")
            ]
        ]
        await query.message.reply_text(
            "⚠️ Are you sure you want to delete this transaction?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cfm_del_"):
        # 2. Perform Deletion
        tx_id = int(data.split("_")[2])
        # We need to fetch it to revert balance
        tx = db.get(Transaction, tx_id)
        if tx:
            # Revert Balance Logic
            if tx.asset_id:
                asset = db.get(Asset, tx.asset_id)
                if asset:
                    if tx.type == "EXPENSE":
                        if asset.type == 'CREDIT':
                            asset.balance -= tx.amount # Reverse credit charge
                        else:
                            asset.balance += tx.amount # Refund to liquid
                    elif tx.type == "INCOME":
                        if asset.type == 'CREDIT':
                            asset.balance += tx.amount 
                        else:
                            asset.balance -= tx.amount
            
            db.delete(tx)
            db.commit()
            await query.message.edit_text(f"Transaction {tx_id} deleted and balance reverted.")
        else:
            await query.message.edit_text("Transaction not found or already deleted.")

    elif data == "cancel_del":
        await query.message.edit_text("Deletion cancelled.")

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
                asset_msg = f"\n{asset.name} balance updated: {asset.balance:.2f}"
        
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
            if len(args) > 2: asset.type = category.upper() # Treat 3rd arg as TYPE in new design
        else:
            # Default type LIQUID unless specified
            asset_type = category.upper() if len(args) > 2 else "LIQUID"
            asset = Asset(name=name, balance=amount, category="General", type=asset_type)
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
            
        # Logic update for Liability/Credit
        if from_asset.type == 'CREDIT':
            from_asset.balance += amount # Cash advance increases debt
        else:
            from_asset.balance -= amount
            
        if to_asset.type == 'CREDIT':
            to_asset.balance -= amount # Paying credit reduces debt
        else:
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

async def handle_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show last 10 transactions with delete option."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    db = next(get_db())
    txs = db.query(Transaction).order_by(Transaction.date.desc()).limit(10).all()
    
    if not txs:
        await update.message.reply_text("No transactions found.")
        return
        
    await update.message.reply_text("Last 10 Transactions:")
    
    for tx in txs:
        # Inline button for each? Too many messages.
        # Better: List them, and provide a /delete <id> command or just a simplified view.
        # Professional UI: Send a message for each? No, spammy.
        # Compromise: Text list, with [Delete] button using a callback that prompts for ID?
        # Actually, let's just make the LAST 5 interactive.
        pass

    for i, tx in enumerate(txs[:5]): # Only show buttons for top 5 to avoid clutter
        keyboard = [[InlineKeyboardButton("Delete", callback_data=f"del_{tx.id}")]]
        msg = f"{tx.date.strftime('%Y-%m-%d')} | {tx.category} | {tx.amount} {tx.currency}\n{tx.description or ''}"
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export all transactions to CSV."""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    import csv
    from io import StringIO
    
    db = next(get_db())
    txs = db.query(Transaction).order_by(Transaction.date.desc()).all()
    
    if not txs:
        await update.message.reply_text("No data to export.")
        return
        
    await update.message.reply_text("Generating CSV...")
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Type', 'Category', 'Amount', 'Currency', 'Description', 'Asset', 'Raw Text'])
    
    for tx in txs:
        asset_name = tx.asset.name if tx.asset else "N/A"
        writer.writerow([
            tx.id, tx.date, tx.type, tx.category, tx.amount, tx.currency, 
            tx.description, asset_name, tx.raw_text
        ])
        
    output.seek(0)
    
    # Send as document
    # Need bytes
    from io import BytesIO
    bytes_output = BytesIO(output.getvalue().encode('utf-8'))
    filename = f"transactions_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await update.message.reply_document(document=bytes_output, filename=filename)


async def handle_budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View status or set budget: /budget <category> <limit>"""
    if update.effective_user.id != ALLOWED_USER_ID: return
    
    args = context.args
    db = next(get_db())
    from db.models import Budget
    
    # Mode 1: View Status
    if not args:
        analyzer = FinanceAnalyzer(db)
        report = analyzer.get_budget_status()
        await update.message.reply_text(report, parse_mode='Markdown')
        return
        
    # Mode 2: Set Budget
    if len(args) < 2:
        await update.message.reply_text("Usage: /budget <category> <limit>")
        return
        
    category = args[0]
    try:
        limit = float(args[1])
        budget = db.query(Budget).filter(Budget.category.ilike(category)).first()
        if budget:
            budget.limit_amount = limit
        else:
            budget = Budget(category=category, limit_amount=limit)
            db.add(budget)
            
        db.commit()
        await update.message.reply_text(f"Budget for {category} set to {limit:.2f}")
    except ValueError:
        await update.message.reply_text("Invalid limit amount.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

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
                    # Logic update for Liability/Credit
                    if from_asset.type == 'CREDIT':
                        from_asset.balance += amount
                    else:
                        from_asset.balance -= amount
                        
                    if to_asset.type == 'CREDIT':
                        to_asset.balance -= amount
                    else:
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

        # Case 3: Log Transaction Details
        if context.user_data.get('expect_log_details'):
            parts = text.split(maxsplit=1)
            try:
                amount = float(parts[0])
                rest = parts[1] if len(parts) > 1 else "General"
                
                # Simple parsing: first word after number is category? 
                # Let's say: "50 Lunch at McD" -> Cat: Lunch, Desc: at McD
                cat_parts = rest.split(maxsplit=1)
                category = cat_parts[0]
                desc = cat_parts[1] if len(cat_parts) > 1 else ""
                
                context.user_data['log_data'] = {
                    'amount': abs(amount),
                    'type': 'EXPENSE' if amount > 0 else 'INCOME', # Assuming user types positive for expense in this flow?
                    # Actually, let's assume positive input = Expense unless specified otherwise
                    # Or simpler: always Expense for now, unless /add used
                    'category': category,
                    'desc': desc
                }
                context.user_data.pop('expect_log_details')
                
                # Ask for Source
                db = next(get_db())
                assets = db.query(Asset).all()
                keyboard = []
                for a in assets:
                    keyboard.append([InlineKeyboardButton(f"{a.name} ({a.type})", callback_data=f"sel_src_{a.id}")])
                
                await update.message.reply_text(
                    f"Got it: {amount} for {category}.\nSelect Payment Source:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            except ValueError:
                await update.message.reply_text("Invalid format. Please start with a number (e.g. '50 Lunch').")
                return

    # Handle Main Menu Buttons
    if text == "Wallet":
        await handle_wallet_command(update, context)
        return
    elif text == "Log Transaction":
        await update.message.reply_text("Enter amount and category (e.g., '50 Lunch'):")
        context.user_data['expect_log_details'] = True
        return
    elif text == "Report":
        await handle_report(update, context)
        return
    elif text == "Add Record":
        await update.message.reply_text("Just send me a message like 'Lunch 50' or 'Payday 5000 via Alipay'")
        return
    elif text == "Budget":
        await handle_budget_command(update, context)
        return
    elif text == "Analytics":
        # Redirect to Report for now, which includes trends
        await handle_report(update, context)
        return
    elif text == "History":
        await handle_history_command(update, context)
        return
    elif text == "More":
        await update.message.reply_text("More commands: /export, /start, /setbalance")
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
    application.add_handler(CommandHandler("wallet", handle_wallet_command))
    application.add_handler(CommandHandler("budget", handle_budget_command))
    application.add_handler(CommandHandler("history", handle_history_command))
    application.add_handler(CommandHandler("export", handle_export_command))
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
