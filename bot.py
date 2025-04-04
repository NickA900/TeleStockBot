import os
import logging
import httpx
from bs4 import BeautifulSoup
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

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Define conversation states
MAIN_MENU, SEARCH_STOCK, HANDLE_STOCK_SELECTION, REMOVE_STOCK, MORE_RESULTS = range(5)

# User alert tracking
user_alerts = {}

# Function to fetch stock suggestions from Google search
def get_stock_suggestions(query, page=1):
    search_url = f"https://www.google.com/search?q={query}+stock+price&start={(page-1)*10}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = httpx.get(search_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("h3")
            return [result.get_text() for result in results[:5]] or ["No results found."]
    except Exception as e:
        return [f"Error fetching results: {str(e)}"]

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Stock", callback_data="search")],
        [InlineKeyboardButton("📌 Existing Alerts", callback_data="existing")],
        [InlineKeyboardButton("❌ Remove Stock", callback_data="remove")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📈 *Welcome to TeleStockBot!*", reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "search":
        await query.edit_message_text("📊 *Enter stock name to search:*", parse_mode="Markdown")
        return SEARCH_STOCK
    elif action == "existing":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        msg = "📌 *Your current alerts:*\n" + "\n".join(stocks) if stocks else "You have no stock alerts."
        await query.edit_message_text(msg, parse_mode="Markdown")
        return MAIN_MENU
    elif action == "remove":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("🚫 No stocks to remove.")
            return MAIN_MENU
        keyboard = [[InlineKeyboardButton(stock, callback_data=f"remove_{stock}")] for stock in stocks]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ *Select stock to remove:*", reply_markup=reply_markup, parse_mode="Markdown")
        return REMOVE_STOCK

async def search_stock(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    matches = get_stock_suggestions(text)

    if not matches:
        await update.message.reply_text("❌ No matching stocks found.")
        return MAIN_MENU

    keyboard = [[InlineKeyboardButton(stock, callback_data=f"select_{stock}")] for stock in matches]
    keyboard.append([InlineKeyboardButton("🔄 Show More Results", callback_data=f"more_{text}_2")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔍 *Select a stock:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

async def handle_stock_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data.replace("select_", "")
    user_id = str(update.effective_user.id)
    
    if stock not in user_alerts.get(user_id, []):
        user_alerts.setdefault(user_id, []).append(stock)
        await query.edit_message_text(f"✅ *Alert set for {stock}!*", parse_mode="Markdown")
    else:
        await query.edit_message_text(f"⚠️ *Already tracking {stock}.*", parse_mode="Markdown")

    return MAIN_MENU

async def remove_stock(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data.replace("remove_", "")
    user_id = str(update.effective_user.id)
    
    if stock in user_alerts.get(user_id, []):
        user_alerts[user_id].remove(stock)
        await query.edit_message_text(f"❌ *Removed alert for {stock}.*", parse_mode="Markdown")
    return MAIN_MENU

async def show_more_results(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    _, stock_query, page = query.data.split("_")
    new_page = int(page)
    matches = get_stock_suggestions(stock_query, new_page)

    keyboard = [[InlineKeyboardButton(stock, callback_data=f"select_{stock}")] for stock in matches]
    keyboard.append([InlineKeyboardButton("🔄 Show More Results", callback_data=f"more_{stock_query}_{new_page+1}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🔍 *More search results:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler, per_message=True)],
            SEARCH_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock)],
            HANDLE_STOCK_SELECTION: [CallbackQueryHandler(handle_stock_selection, per_message=True)],
            REMOVE_STOCK: [CallbackQueryHandler(remove_stock, per_message=True)],
            MORE_RESULTS: [CallbackQueryHandler(show_more_results, per_message=True)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()import os
import logging
import httpx
from bs4 import BeautifulSoup
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

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Define conversation states
MAIN_MENU, SEARCH_STOCK, HANDLE_STOCK_SELECTION, REMOVE_STOCK, MORE_RESULTS = range(5)

# User alert tracking
user_alerts = {}

# Function to fetch stock suggestions from Google search
def get_stock_suggestions(query, page=1):
    search_url = f"https://www.google.com/search?q={query}+stock+price&start={(page-1)*10}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = httpx.get(search_url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("h3")
            return [result.get_text() for result in results[:5]] or ["No results found."]
    except Exception as e:
        return [f"Error fetching results: {str(e)}"]

async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Stock", callback_data="search")],
        [InlineKeyboardButton("📌 Existing Alerts", callback_data="existing")],
        [InlineKeyboardButton("❌ Remove Stock", callback_data="remove")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📈 *Welcome to TeleStockBot!*", reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "search":
        await query.edit_message_text("📊 *Enter stock name to search:*", parse_mode="Markdown")
        return SEARCH_STOCK
    elif action == "existing":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        msg = "📌 *Your current alerts:*\n" + "\n".join(stocks) if stocks else "You have no stock alerts."
        await query.edit_message_text(msg, parse_mode="Markdown")
        return MAIN_MENU
    elif action == "remove":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("🚫 No stocks to remove.")
            return MAIN_MENU
        keyboard = [[InlineKeyboardButton(stock, callback_data=f"remove_{stock}")] for stock in stocks]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ *Select stock to remove:*", reply_markup=reply_markup, parse_mode="Markdown")
        return REMOVE_STOCK

async def search_stock(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    matches = get_stock_suggestions(text)

    if not matches:
        await update.message.reply_text("❌ No matching stocks found.")
        return MAIN_MENU

    keyboard = [[InlineKeyboardButton(stock, callback_data=f"select_{stock}")] for stock in matches]
    keyboard.append([InlineKeyboardButton("🔄 Show More Results", callback_data=f"more_{text}_2")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔍 *Select a stock:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

async def handle_stock_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data.replace("select_", "")
    user_id = str(update.effective_user.id)
    
    if stock not in user_alerts.get(user_id, []):
        user_alerts.setdefault(user_id, []).append(stock)
        await query.edit_message_text(f"✅ *Alert set for {stock}!*", parse_mode="Markdown")
    else:
        await query.edit_message_text(f"⚠️ *Already tracking {stock}.*", parse_mode="Markdown")

    return MAIN_MENU

async def remove_stock(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data.replace("remove_", "")
    user_id = str(update.effective_user.id)
    
    if stock in user_alerts.get(user_id, []):
        user_alerts[user_id].remove(stock)
        await query.edit_message_text(f"❌ *Removed alert for {stock}.*", parse_mode="Markdown")
    return MAIN_MENU

async def show_more_results(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    _, stock_query, page = query.data.split("_")
    new_page = int(page)
    matches = get_stock_suggestions(stock_query, new_page)

    keyboard = [[InlineKeyboardButton(stock, callback_data=f"select_{stock}")] for stock in matches]
    keyboard.append([InlineKeyboardButton("🔄 Show More Results", callback_data=f"more_{stock_query}_{new_page+1}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🔍 *More search results:*", reply_markup=reply_markup, parse_mode="Markdown")
    return HANDLE_STOCK_SELECTION

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler, per_message=True)],
            SEARCH_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock)],
            HANDLE_STOCK_SELECTION: [CallbackQueryHandler(handle_stock_selection, per_message=True)],
            REMOVE_STOCK: [CallbackQueryHandler(remove_stock, per_message=True)],
            MORE_RESULTS: [CallbackQueryHandler(show_more_results, per_message=True)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
