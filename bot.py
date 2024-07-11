from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler,  MessageHandler, filters, CallbackQueryHandler, ContextTypes
from pymongo import MongoClient
import random

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['telegram_bot']
collection = db['user_requests']

# Bot token from BotFather
BOT_TOKEN = '7467036797:AAE9OQj8ZtAvGg4jvnwGCXMmX6BRI21mUPM'
ADMIN_ID = '2135064059'
messages_query = ["✈️ZBURĂ!", "📡Sari peste 1 runda", "📡Sari peste runda 2", "✈️ZBURĂ!", "📡Sari peste 3 runde"]

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_record = collection.find_one({'user_id': user.id})

    if user_record:
        if user_record['status'] == 'approved':
            keyboard = [
                [KeyboardButton("💸Obțineți semnal💸")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Bine ai revenit! Ai acces la bot.", reply_markup=reply_markup)
            
            await update.message.reply_text("Выполнить действие",
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("❓ Merită să zbori înăuntru ❓", callback_data="question")],
                                                [InlineKeyboardButton("🌸 Primiți un semnal 🌸", callback_data="signal")]
                                            ]))
        elif user_record['status'] == 'pending':
            await update.message.reply_text("Solicitarea dvs. este încă în așteptare.")
        elif user_record['status'] == 'rejected':
            await update.message.reply_text("Solicitarea dvs. a fost respinsă. Vă rugăm să contactați administratorul.")
    else:
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'status': 'pending'
        }
        collection.insert_one(user_data)
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Solicitare nouă de înscriere de la @{user.username}",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("Aproba", callback_data=f"approve_{user.id}")],
                                           [InlineKeyboardButton("Respinge", callback_data=f"reject_{user.id}")]
                                       ]))
        await update.message.reply_text("Solicitarea ta de înscriere a fost trimisă administratorului.")

# Handler for callback queries from inline keyboard buttons
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data.split('_')
    action, user_id = data[0], int(data[1])
    
    if action == 'approve':
        collection.update_one({'user_id': user_id}, {'$set': {'status': 'approved'}})
        await context.bot.send_message(
            chat_id=user_id,
            text="Выполнить действие",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("💸Obțineți semnal💸")]], resize_keyboard=True)
        )
        await context.bot.send_message(chat_id=user_id, text="Выполнить действие",
                                       reply_markup=InlineKeyboardMarkup([
                                           [InlineKeyboardButton("❓ Merită să zbori înăuntru ❓", callback_data="question")],
                                           [InlineKeyboardButton("🌸 Primiți un semnal 🌸", callback_data="signal")]
                                       ]))
    elif action == 'reject':
        collection.update_one({'user_id': user_id}, {'$set': {'status': 'rejected'}})
        await context.bot.send_message(chat_id=user_id, text="Solicitarea dvs. de a vă alătura botului a fost respinsă.")
    
    await query.answer()
async def get_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [       
        [KeyboardButton("💸Obțineți semnal💸")],
        [KeyboardButton("❓MERITĂ SĂ ZBOR❓")]
    ]
    random_number = round(random.uniform(1.0, 2.49), 2)
    message = f"🚀{random_number}Х"
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(message, reply_markup=reply_markup)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("💸Obțineți semnal💸")]
    ]
    message = random.choice(messages_query)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(message, reply_markup=reply_markup)
async def ask_question1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("💸Obțineți semnal💸")]
    ]
    message = random.choice(messages_query)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("message", reply_markup=reply_markup)    
# Handlers for the inline buttons
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    message = random.choice(messages_query)
    await query.message.reply_text(message)

async def handle_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    message = random.choice(messages_query)
    await query.message.reply_text(message)

# Handler for the /get_id command
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    await update.message.reply_text(f"ID-ul dvs. de utilizator este {user_id}")
    
# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_id", get_id))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern='approve|reject'))
    application.add_handler(CallbackQueryHandler(handle_question, pattern='question'))
    application.add_handler(CallbackQueryHandler(handle_signal, pattern='signal'))
    application.add_handler(MessageHandler(filters.Text("💸Obțineți semnal💸"), get_signal))
    application.add_handler(MessageHandler(filters.Text("❓MERITĂ SĂ ZBOR❓"), ask_question))
    application.add_handler(MessageHandler(filters.Text(messages_query), ask_question1))

    application.run_polling()

if __name__ == '__main__':
    main()
