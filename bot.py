import os
import requests
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
import schedule
import time
from threading import Thread

# Get Telegram Token from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Initialize Telegram Bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Store user preferences (Alerts, Companies, etc.)
user_data = {}

# Function to fetch stock prices (Replace with real API if needed)
def get_stock_price(company):
    stock_prices = {
        "Jupiter Wagons": 330,
        "Suzlon Energy": 55,
        "Trident": 24
    }  # Mock Data
    return stock_prices.get(company, "Unknown")

# Function to handle /start command
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Set Price Alert", callback_data='set_alert')],
        [InlineKeyboardButton("Weekly Analysis Report", callback_data='weekly_report')],
        [InlineKeyboardButton("Manage Companies", callback_data='manage_companies')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome to Stock Alert Bot! Choose an option:", reply_markup=reply_markup)

# Function to handle button clicks
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == "set_alert":
        query.message.reply_text("Enter the company name and price (e.g., 'Jupiter Wagons 320')")
    elif query.data == "weekly_report":
        query.message.reply_text("Generating weekly report... (Mock Data: Jupiter Wagons ₹330, Trend: Bullish)")
    elif query.data == "manage_companies":
        query.message.reply_text("Send /add to add a company, /remove to remove.")

# Function to handle stock alerts
def set_alert(update: Update, context: CallbackContext):
    message = update.message.text.split()
    if len(message) < 2:
        update.message.reply_text("Invalid format! Use: CompanyName Price")
        return
    
    company = " ".join(message[:-1])
    try:
        price = float(message[-1])
        user_data[update.message.chat_id] = {"company": company, "price": price}
        update.message.reply_text(f"Alert set for {company} at ₹{price}.")
    except ValueError:
        update.message.reply_text("Invalid price! Please enter a numeric value.")

# Function to send alerts when condition is met
def check_alerts():
    for chat_id, alert in list(user_data.items()):  # Use list() to avoid runtime errors
        current_price = get_stock_price(alert['company'])
        if current_price != "Unknown" and current_price <= alert['price']:
            bot.send_message(chat_id=chat_id, text=f"ALERT: {alert['company']} has reached ₹{current_price}!")
            del user_data[chat_id]  # Remove alert after triggering

# Function to run scheduled tasks
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(10)

# Setting up Telegram bot handlers
application = Application.builder().token(TELEGRAM_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_alert))

# Run the scheduler in a separate thread
schedule.every(30).seconds.do(check_alerts)
Thread(target=run_schedule, daemon=True).start()

# Start the bot
application.run_polling()
