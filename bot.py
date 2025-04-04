import os
import logging
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Ensure the token is valid
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing. Please set it in your .env file.")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Define conversation states
MAIN_MENU, SEARCH_STOCK, HANDLE_STOCK_SELECTION, REMOVE_STOCK = range(4)

# User alert tracking
user_alerts = {}

# Function to fetch stock suggestions from a search engine
def get_stock_suggestions(query):
    search_url = f"https://www.google.com/search?q={query}+stock+price"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = httpx.get(search_url, headers=headers)
        if response.status_code == 200:
            return [f"{query} Stock - Result {i+1}" for i in range(5)]
        return ["No results found."]
    except Exception as e:
        return [f"Error fetching results: {str(e)}"]

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Stock", callback_data="search")],
        [InlineKeyboardButton("📈 Existing Alerts", callback_data="existing")],
        [InlineKeyboardButton("❌ Remove Stock", callback_data="remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to *TeleStockBot*! Choose an option:", reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "search":
        await query.edit_message_text("Enter stock name to search:")
        return SEARCH_STOCK
    elif action == "existing":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("⚠️ You have no existing stock alerts.")
        else:
            msg = "📊 *Your current alerts:*\n" + "\n".join([f"- {s}" for s in stocks])
            await query.edit_message_text(msg, parse_mode="Markdown")
        return MAIN_MENU
    elif action == "remove":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("⚠️ You have no stocks to remove.")
            return MAIN_MENU
        keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in stocks]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📉 *Select stock to remove:*", reply_markup=reply_markup, parse_mode="Markdown")
        return REMOVE_STOCK

async def search_stock(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    matches = get_stock_suggestions(text)

    if not matches:
        await update.message.reply_text("⚠️ No matching stocks found.")
        return MAIN_MENU

    keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in matches]
    keyboard.append([InlineKeyboardButton("🔄 Show More Results", callback_data=f"more_{text}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📈 *Select a stock:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

async def show_more_results(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock_query = query.data.replace("more_", "")
    matches = get_stock_suggestions(stock_query)

    keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in matches]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("📈 *More stock results:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

async def handle_stock_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data
    context.user_data["selected_stock"] = stock
    user_id = str(update.effective_user.id)
    
    if stock not in user_alerts.get(user_id, []):
        user_alerts.setdefault(user_id, []).append(stock)
        await query.edit_message_text(f"✅ Alert set for *{stock}*!", parse_mode="Markdown")
    else:
        await query.edit_message_text(f"⚠️ Already tracking *{stock}*.", parse_mode="Markdown")

    return MAIN_MENU

async def remove_stock(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data
    user_id = str(update.effective_user.id)
    
    if stock in user_alerts.get(user_id, []):
        user_alerts[user_id].remove(stock)
        await query.edit_message_text(f"❌ Removed alert for *{stock}*.", parse_mode="Markdown")
    return MAIN_MENU

async def back_to_menu(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Stock", callback_data="search")],
        [InlineKeyboardButton("📈 Existing Alerts", callback_data="existing")],
        [InlineKeyboardButton("❌ Remove Stock", callback_data="remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 *Main Menu:*", reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_handler),
                CommandHandler("menu", back_to_menu)
            ],
            SEARCH_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock)],
            HANDLE_STOCK_SELECTION: [
                CallbackQueryHandler(handle_stock_selection),
                CallbackQueryHandler(show_more_results, pattern="^more_"),
            ],
            REMOVE_STOCK: [CallbackQueryHandler(remove_stock)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
