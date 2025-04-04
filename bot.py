import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8443))

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Define conversation states
MAIN_MENU, SEARCH_STOCK, HANDLE_STOCK_SELECTION, REMOVE_STOCK = range(4)

# User alert tracking
user_alerts = {}

# Simulated stock database
mock_stock_data = {
    "Phillips": {
        "price": 210,
        "details": "Philips India Limited manufactures and markets consumer electronics. Sector: Consumer Durables, P/E: 22.5, ROE: 18%",
    },
    "Philippines Chilli": {
        "price": 105,
        "details": "Philippines Chilli Exports Ltd - Sector: Agriculture, Volatility: High, P/E: 11.2",
    },
    "Phillips Trimmer": {
        "price": 325,
        "details": "Phillips Trimmer Ltd - Sector: Personal Care Products, P/E: 15.9, Good Market Penetration",
    },
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Search Stock", callback_data="search"),
            InlineKeyboardButton("New Stock Alert", callback_data="add"),
        ],
        [
            InlineKeyboardButton("Existing Stock Alerts", callback_data="existing"),
            InlineKeyboardButton("Remove Stock", callback_data="remove"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to TeleStockBot!", reply_markup=reply_markup)
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "search" or action == "add":
        context.user_data["add_mode"] = action == "add"
        await query.edit_message_text("Enter stock name to search:")
        return SEARCH_STOCK

    elif action == "existing":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("You have no existing stock alerts.")
        else:
            msg = "Your current alerts:\n" + "\n".join(stocks)
            await query.edit_message_text(msg)
        return MAIN_MENU

    elif action == "remove":
        user_id = str(update.effective_user.id)
        stocks = user_alerts.get(user_id, [])
        if not stocks:
            await query.edit_message_text("You have no stocks to remove.")
            return MAIN_MENU
        keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in stocks]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select stock to remove:", reply_markup=reply_markup)
        return REMOVE_STOCK

async def search_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    matches = [name for name in mock_stock_data if text in name.lower()]

    if not matches:
        await update.message.reply_text("No matching stocks found.")
        return MAIN_MENU

    keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in matches]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a stock:", reply_markup=reply_markup)
    return HANDLE_STOCK_SELECTION

async def handle_stock_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock = query.data
    context.user_data["selected_stock"] = stock

    if context.user_data.get("add_mode"):
        keyboard = [
            [
                InlineKeyboardButton("Set Alert", callback_data="set_alert"),
                InlineKeyboardButton("Detailed Info", callback_data="details"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"You selected: {stock}", reply_markup=reply_markup)
        return HANDLE_STOCK_SELECTION
    else:
        price = mock_stock_data[stock]["price"]
        await query.edit_message_text(f"Current price of {stock}: ₹{price}")
        return MAIN_MENU

async def handle_alert_or_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    stock = context.user_data.get("selected_stock")
    user_id = str(update.effective_user.id)

    if action == "set_alert":
        if stock not in user_alerts.get(user_id, []):
            user_alerts.setdefault(user_id, []).append(stock)
        await query.edit_message_text(f"Alert set for {stock}!")

    elif action == "details":
        details = mock_stock_data[stock]["details"]
        await query.edit_message_text(f"Details for {stock}:\n{details}")

    return MAIN_MENU

async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock = query.data
    user_id = str(update.effective_user.id)
    
    if stock in user_alerts.get(user_id, []):
        user_alerts[user_id].remove(stock)
        await query.edit_message_text(f"Removed alert for {stock}.")
    
    return MAIN_MENU

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler)],
            SEARCH_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock)],
            HANDLE_STOCK_SELECTION: [CallbackQueryHandler(handle_alert_or_info)],
            REMOVE_STOCK: [CallbackQueryHandler(remove_stock)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
