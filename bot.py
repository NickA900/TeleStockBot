import os
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CallbackContext, CallbackQueryHandler, 
                          CommandHandler, MessageHandler, filters, ConversationHandler)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API keys and tokens
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

print("TELEGRAM_BOT_TOKEN:", TELEGRAM_BOT_TOKEN)
print("FINNHUB_API_KEY:", FINNHUB_API_KEY)

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Conversation states
SEARCH, SET_ALERT, REMOVE_ALERT = range(3)
user_alerts = {}

# Start command handler
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Search Stock", callback_data="search")],
        [InlineKeyboardButton("Existing Stock Alerts", callback_data="alerts")],
        [InlineKeyboardButton("Add More", callback_data="add")],
        [InlineKeyboardButton("Remove Alert", callback_data="remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

# Button handler for the options menu
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "search":
        await query.message.reply_text("Provide stock name:")
        return SEARCH
    elif query.data == "alerts":
        alert_list = "\n".join([f"{stock}: {price}" for stock, price in user_alerts.items()]) or "No alerts set."
        await query.message.reply_text(alert_list)
    elif query.data == "add":
        await query.message.reply_text("Provide stock name:")
        return SEARCH
    elif query.data == "remove":
        if user_alerts:
            keyboard = [[InlineKeyboardButton(stock, callback_data=f"remove_{stock}")] for stock in user_alerts]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Select stock to remove:", reply_markup=reply_markup)
            return REMOVE_ALERT
        else:
            await query.message.reply_text("No alerts to remove.")

# Search for stock by name (FIXED)
async def search_stock(update: Update, context: CallbackContext):
    stock_name = update.message.text
    url = f"https://finnhub.io/api/v1/search?q={stock_name}&token={FINNHUB_API_KEY}"
    
    try:
        response = requests.get(url).json()
        print("Finnhub API Response:", response)  # Debugging output

        if response.get("result"):
            keyboard = [[InlineKeyboardButton(stock["description"], callback_data=f"select_{stock['symbol']}")] for stock in response["result"]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select a stock:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("No results found.")
    except Exception as e:
        print("Error fetching stock data:", e)
        await update.message.reply_text("Error fetching stock data. Try again later.")

# Select a stock from the search results
async def select_stock(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split("_")[1]
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
    
    try:
        data = requests.get(url).json()
        message = f"{symbol} \nCurrent Price: {data['c']} \nHigh: {data['h']} \nLow: {data['l']}"

        keyboard = [
            [InlineKeyboardButton("Set Alert", callback_data=f"alert_{symbol}")],
            [InlineKeyboardButton("Show More Stocks", callback_data="search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        print("Error fetching stock details:", e)
        await query.message.reply_text("Error fetching stock details. Try again later.")

# Set price alert for a stock
async def set_alert(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split("_")[1]
    user_alerts[symbol] = None
    await query.message.reply_text(f"Set price alert for {symbol} (reply with price):")
    return SET_ALERT

# Save the alert price
async def save_alert(update: Update, context: CallbackContext):
    try:
        price = float(update.message.text)
        stock = list(user_alerts.keys())[-1]
        user_alerts[stock] = price
        await update.message.reply_text(f"Alert set for {stock} at {price}")
    except ValueError:
        await update.message.reply_text("Invalid price. Please enter a valid number.")
    return ConversationHandler.END

# Remove alert for a stock
async def remove_alert(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    stock = query.data.split("_")[1]
    user_alerts.pop(stock, None)
    await query.message.reply_text(f"Removed alert for {stock}")
    return ConversationHandler.END

# Check and send alerts when stock reaches target price
async def check_alerts(context: CallbackContext):
    for stock, target_price in user_alerts.items():
        url = f"https://finnhub.io/api/v1/quote?symbol={stock}&token={FINNHUB_API_KEY}"
        try:
            data = requests.get(url).json()
            current_price = data.get("c")
            if current_price and target_price and current_price <= target_price:
                await context.bot.send_message(chat_id=context.job.chat_id, text=f"{stock} reached your alert price: {target_price}")
        except Exception as e:
            print(f"Error checking alerts for {stock}:", e)

# Create the application and add handlers
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock)],
        SET_ALERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_alert)],
        REMOVE_ALERT: [CallbackQueryHandler(remove_alert, pattern="^remove_")]
    },
    fallbacks=[]
)

application.add_handler(conv_handler)
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(CallbackQueryHandler(select_stock, pattern="^select_"))
application.add_handler(CallbackQueryHandler(set_alert, pattern="^alert_"))

# **Fix Job Queue Issue**
job_queue = application.job_queue
job_queue.run_repeating(check_alerts, interval=3600)

# Start the bot polling
application.run_polling()
