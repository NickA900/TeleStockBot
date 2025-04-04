
import os
import asyncio
import logging
import time
from dotenv import load_dotenv
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler

# Load Environment Variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Check if token exists
if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN. Set it in your environment or .env file.")

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Store user preferences (Alerts, Companies, etc.)
user_data = {}

# Mock function to fetch stock prices (Replace with real API if needed)
def get_stock_price(company):
    stock_prices = {
        "Jupiter Wagons": 330,
        "Suzlon Energy": 55,
        "Trident": 24
    }
    return stock_prices.get(company, "Unknown")

# /start command handler
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔎 Search Stock", callback_data='search_stock')],
        [InlineKeyboardButton("➕ New Stock Alert", callback_data='set_alert')],
        [InlineKeyboardButton("📋 Existing Stock Alerts", callback_data='list_alerts')],
        [InlineKeyboardButton("⚙️ Manage Stocks", callback_data='manage_stocks')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Stock Alert Bot! Choose an option:", reply_markup=reply_markup)

# Button click handler
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "search_stock":
        await query.message.reply_text("Enter the stock name to search (e.g., 'Jupiter Wagons').")
    elif query.data == "set_alert":
        await query.message.reply_text("Enter the company name and price (e.g., 'Jupiter Wagons 320').")
    elif query.data == "list_alerts":
        chat_id = query.message.chat_id
        if chat_id in user_data and user_data[chat_id]:
            alerts = "\n".join([f"{d['company']} - ₹{d['price']}" for d in user_data[chat_id]])
            await query.message.reply_text(f"Your active alerts:\n{alerts}")
        else:
            await query.message.reply_text("No alerts set.")
    elif query.data == "manage_stocks":
        await query.message.reply_text("Send /add to add a stock or /remove to remove.")

# Search stock function
async def search_stock(update: Update, context: CallbackContext):
    company = update.message.text.strip()
    price = get_stock_price(company)
    if price == "Unknown":
        await update.message.reply_text(f"Stock '{company}' not found!")
    else:
        await update.message.reply_text(f"{company} is currently at ₹{price}")

# Stock alert handler
async def set_alert(update: Update, context: CallbackContext):
    message = update.message.text.split()
    if len(message) < 2:
        await update.message.reply_text("Invalid format! Use: CompanyName Price")
        return

    company = " ".join(message[:-1])
    try:
        price = float(message[-1])
    except ValueError:
        await update.message.reply_text("Invalid price! Please enter a valid number.")
        return

    chat_id = update.message.chat_id
    if chat_id not in user_data:
        user_data[chat_id] = []

    user_data[chat_id].append({"company": company, "price": price})
    await update.message.reply_text(f"Alert set for {company} at ₹{price}.")

# Alert checking function
async def check_alerts(application):
    to_remove = []
    for chat_id, alerts in user_data.items():
        for alert in alerts:
            current_price = get_stock_price(alert['company'])
            if current_price != "Unknown" and current_price <= alert['price']:
                await application.bot.send_message(chat_id=chat_id, text=f"🚨 ALERT: {alert['company']} has reached ₹{current_price}!")
                to_remove.append((chat_id, alert))

    for chat_id, alert in to_remove:
        user_data[chat_id].remove(alert)

# Function to run scheduled tasks
def run_schedule(application):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        loop.run_until_complete(check_alerts(application))
        time.sleep(30)

# Main function to run bot
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_alert))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_stock))

    # Run scheduler in a separate thread
    Thread(target=run_schedule, args=(application,), daemon=True).start()

    application.run_polling()

if __name__ == "__main__":
    main()
