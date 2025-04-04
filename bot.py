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
from dotenv import load_dotenv  # Load environment variables
load_dotenv() TOKEN = os.getenv("BOT_TOKEN") PORT = int(os.environ.get("PORT", 8443))

logging.basicConfig( format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, )

Define conversation states

MAIN_MENU, SEARCH_STOCK, HANDLE_STOCK_SELECTION, REMOVE_STOCK = range(4)

User alert tracking

user_alerts = {}

async def search_stock_online(query): """Fetch stock search suggestions from Yahoo Finance.""" url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}" async with httpx.AsyncClient() as client: response = await client.get(url) if response.status_code == 200: data = response.json() return [item['shortname'] for item in data.get('quotes', []) if 'shortname' in item] return []

async def start(update: Update, context: CallbackContext): keyboard = [ [ InlineKeyboardButton("Search Stock", callback_data="search"), InlineKeyboardButton("New Stock Alert", callback_data="add"), ], [ InlineKeyboardButton("Existing Stock Alerts", callback_data="existing"), InlineKeyboardButton("Remove Stock", callback_data="remove"), ], ] reply_markup = InlineKeyboardMarkup(keyboard) await update.message.reply_text("Welcome to TeleStockBot!", reply_markup=reply_markup) return MAIN_MENU

async def main_menu_handler(update: Update, context: CallbackContext): query = update.callback_query await query.answer() action = query.data

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

async def search_stock(update: Update, context: CallbackContext): text = update.message.text.lower() matches = await search_stock_online(text)

if not matches:
    await update.message.reply_text("No matching stocks found.")
    return MAIN_MENU

keyboard = [[InlineKeyboardButton(stock, callback_data=stock)] for stock in matches]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text("Select a stock:", reply_markup=reply_markup)
return HANDLE_STOCK_SELECTION

async def handle_stock_selection(update: Update, context: CallbackContext): query = update.callback_query await query.answer() stock = query.data context.user_data["selected_stock"] = stock

keyboard = [
    [
        InlineKeyboardButton("Set Alert", callback_data="set_alert"),
        InlineKeyboardButton("Detailed Info", callback_data="details"),
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)
await query.edit_message_text(f"You selected: {stock}", reply_markup=reply_markup)
return HANDLE_STOCK_SELECTION

async def handle_alert_or_info(update: Update, context: CallbackContext): query = update.callback_query await query.answer() action = query.data stock = context.user_data.get("selected_stock") user_id = str(update.effective_user.id)

if action == "set_alert":
    if stock not in user_alerts.get(user_id, []):
        user_alerts.setdefault(user_id, []).append(stock)
    await query.edit_message_text(f"Alert set for {stock}!")
elif action == "details":
    await query.edit_message_text(f"Fetching details for {stock}...")

return MAIN_MENU

async def remove_stock(update: Update, context: CallbackContext): query = update.callback_query await query.answer() stock = query.data user_id = str(update.effective_user.id) if stock in user_alerts.get(user_id, []): user_alerts[user_id].remove(stock) await query.edit_message_text(f"Removed alert for {stock}.") return MAIN_MENU

if name == "main": app = ApplicationBuilder().token(TOKEN).build()

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

