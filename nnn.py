import logging
import mysql.connector
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import qrcode
from io import BytesIO

group_selection = {}
# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# MySQL connection setup
db_config = {
    'user': 'root',
    'password': 'your_mysql_password',
    'host': '127.0.0.1',
    'database': 'ton_bot',
}

# TON wallet setup
# ton_wallet = Wallet('seed words')
TON_API_URL = 'https://toncenter.com/api/v2/'
API_KEY = 'e122761e97f07d98c83e1a323dc1660f6b31b949292d7a3200510e90441d6cd4'  # You need to get an API key from toncenter.com
WALLET_ADDRESS = 'UQBU61PW1hoLoJ4-yJkMRtrTsZD7vhfyfe25jDtDyaXEPpwz'

# Generate QR Code
def generate_qr_code(payment_link):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_link)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    return img

async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user

        if context.user_data.get('state') != 'awaiting_amount_input':
            await update.message.reply_text("Unexpected input. Please follow the workflow.")
            return

        amount_text = update.message.text
        try:
            amount = float(amount_text)
            if amount < 0.1:
                raise ValueError("Amount is less than 0.1 TON")
        except ValueError:
            await update.message.reply_text("Invalid amount. Please enter a valid amount (min 0.1 TON).")
            return

        context.user_data['amount'] = amount
        await update.message.reply_text("Enter any extra data for the transaction:")
        context.user_data['state'] = 'awaiting_extra_data_input'

    except Exception as e:
        logging.error(e)

async def extra_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user

        if context.user_data.get('state') != 'awaiting_extra_data_input':
            await update.message.reply_text("Unexpected input. Please follow the workflow.")
            return

        extra_data = update.message.text
        amount = context.user_data['amount']
        context.user_data['extra_data'] = extra_data

        confirm_text = f"Confirm Transaction:\nAmount: {amount} TON\nExtra Data: {extra_data}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Confirm", callback_data='confirm_transaction')]])

        await update.message.reply_text(confirm_text, reply_markup=keyboard)
        context.user_data['state'] = 'awaiting_confirmation'

    except Exception as e:
        logging.error(e)

async def confirm_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query

        if context.user_data.get('state') != 'awaiting_confirmation':
            await query.message.reply_text("Unexpected input. Please follow the workflow.")
            return

        amount = context.user_data.get('amount')
        extra_data = context.user_data.get('extra_data')
        recipient_address = WALLET_ADDRESS  # Smart Contract Address

        # Generate the payment link (TON Wallet compatible URI)
        payment_link = f"ton://transfer/{recipient_address}?amount={int(amount * 1e9)}&text={extra_data}"
        qr_image = generate_qr_code(payment_link)
        bio = BytesIO()
        qr_image.save(bio, format='PNG')
        bio.seek(0)

        await query.message.reply_photo(photo=bio, caption="Scan this QR code to complete the transaction or use the link below.")
        await query.message.reply_text(payment_link)

    except Exception as e:
        logging.error(e)

# Handler for option selection
async def option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        instance_id, option_name = query.data.split('_')[1:]
        context.user_data['instance_id'] = int(instance_id)
        context.user_data['option_name'] = option_name

        await query.message.reply_text("Enter the transaction amount (min 0.1 TON):")
        context.user_data['state'] = 'awaiting_amount_input'
    
    except Exception as e:
        logging.error(e)


# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(**db_config)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if 'group' not in chat.type:
        await update.message.reply_text("This command can only be used in group chats.")
        return
    
    group_id = chat.id
    formatted_message = f"The group ID is: <code>{group_id}</code>\n\n"
    
    await update.message.reply_text(formatted_message, parse_mode='HTML')

async def copy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    group_id = query.data.split('_')[1]
    
    await query.answer("Copied to clipboard!")  # Show notification to the user
    await query.message.reply_text(f"Group ID {group_id} copied! (Please manually copy it if not auto-copied.)")
    await query.answer()

# Handler for /select_group command in private chat
async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != 'private':
        await update.message.reply_text("This command can only be used in private chat with the bot.")
        return
    await update.message.reply_text("Please enter the group ID to select it:")
    context.user_data['state'] = 'awaiting_group_id'

# Handler for group ID input
async def handle_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'awaiting_group_id':
        await update.message.reply_text("Unexpected input. Please follow the workflow.")
        return

    group_id = update.message.text
    try:
        group_id = int(group_id)
    except ValueError:
        await update.message.reply_text("Invalid group ID. Please enter a numeric group ID.")
        return

    group_selection[update.message.from_user.id] = group_id
    await update.message.reply_text(f"Group ID {group_id} selected successfully.")
    context.user_data['state'] = None

# Handler for /buy command
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat

        if 'group' not in chat.type:
            await update.message.reply_text("This command can only be used in group chats.")
            return

        db_conn = get_db_connection()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM instances WHERE group_id = %s AND status = 'active'", (chat.id,))
        instances = cursor.fetchall()
        cursor.close()
        db_conn.close()

        if not instances:
            await update.message.reply_text("No instances available for this group.")
            return
        
        buttons = [[InlineKeyboardButton(instance['name'], callback_data=f'instance_{instance["id"]}') for instance in instances]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Select an instance:", reply_markup=reply_markup)
        context.user_data['state'] = 'awaiting_instance_selection'
    
    except Exception as e:
        logging.error(e)

# Handler for instance selection
async def instance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        instance_id = int(query.data.split('_')[1])

        db_conn = get_db_connection()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM instances WHERE id = %s", (instance_id,))
        instance = cursor.fetchone()
        cursor.close()
        db_conn.close()

        if not instance:
            await query.answer("Instance not found.")
            return

        context.user_data['instance_id'] = instance_id

        options = instance['options'].split(',')
        buttons = [[InlineKeyboardButton(option, callback_data=f'option_{instance_id}_{option}')] for option in options]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text(f"Options for {instance['name']}:", reply_markup=reply_markup)
        context.user_data['state'] = 'awaiting_option_selection'

    except Exception as e:
        logging.error(e)

# Handler for /create_instance command in private chat
async def create_instance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat

        if chat.type != 'private':
            await update.message.reply_text("This command can only be used in private chat with the bot.")
            return

        if user.id not in group_selection:
            await update.message.reply_text("Please use /select_group to select a group first.")
            return

        await update.message.reply_text("What instance name do you want?")
        context.user_data['state'] = 'awaiting_instance_name'

    except Exception as e:
        logging.error(e)

# Unified state handler
async def state_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        state = context.user_data.get('state')

        if state == 'awaiting_instance_name':
            await handle_instance_name(update, context)
        elif state == 'awaiting_options':
            await handle_options(update, context)
        elif state == 'awaiting_group_id':
            await handle_group_id(update, context)
        elif state == 'awaiting_amount_input':
            await amount_handler(update, context)
        elif state == 'awaiting_extra_data_input':
            await extra_data_handler(update, context)
        else:
            await update.message.reply_text("Unexpected input. Please follow the workflow.")
    
    except Exception as e:
        logging.error(e)

# Handler for receiving instance name
async def handle_instance_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get('state') != 'awaiting_instance_name':
            await update.message.reply_text("Unexpected input. Please follow the workflow.")
            return

        instance_name = update.message.text
        context.user_data['instance_name'] = instance_name

        await update.message.reply_text("List the options (comma-separated):")
        context.user_data['state'] = 'awaiting_options'

    except Exception as e:
        logging.error(e)

# Handler for receiving options
async def handle_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get('state') != 'awaiting_options':
            await update.message.reply_text("Unexpected input. Please follow the workflow.")
            return

        options = update.message.text
        instance_name = context.user_data['instance_name']
        group_id = group_selection[update.message.from_user.id]

        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        cursor.execute(
            "INSERT INTO instances (group_id, name, options, status) "
            "VALUES (%s, %s, %s, %s)",
            (group_id, instance_name, options, 'passive')
        )
        db_conn.commit()
        cursor.close()
        db_conn.close()

        await update.message.reply_text(f"Instance '{instance_name}' created successfully with options: {options}")
        context.user_data.clear()

    except Exception as e:
        logging.error(e)

# Handler for /activate and /close commands
async def list_instances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat

        if user.id not in group_selection:
            await update.message.reply_text("Please use /select_group to select a group first.")
            return

        group_id = group_selection[user.id]
        command = update.message.text.split()[0][1:]

        if command == "activate":
            status = 'passive'
            action = "activate"
        elif command == "close":
            status = 'active'
            action = "close"
        else:
            await update.message.reply_text("Invalid command.")
            return

        db_conn = get_db_connection()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM instances WHERE group_id = %s AND status = %s", (group_id, status))
        instances = cursor.fetchall()
        cursor.close()
        db_conn.close()

        if not instances:
            await update.message.reply_text(f"No {status} instances available for this group.")
            return

        buttons = [[InlineKeyboardButton(instance['name'], callback_data=f'{action}_{instance["name"]}') for instance in instances]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(f"Select an instance to {action}:", reply_markup=reply_markup)
        context.user_data['state'] = f'awaiting_{action}_selection'

    except Exception as e:
        logging.error(e)

# Handler for instance activation or closure
async def activate_or_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        action, instance_name = query.data.split('_', 1)

        user = query.from_user
        group_id = group_selection.get(user.id)

        if not group_id:
            await query.message.reply_text("Please use /select_group to select a group first.")
            return

        db_conn = get_db_connection()
        cursor = db_conn.cursor()
        if action == "activate":
            cursor.execute("UPDATE instances SET status = 'active' WHERE name = %s AND group_id = %s", (instance_name, group_id))
        elif action == "close":
            cursor.execute("UPDATE instances SET status = 'passive' WHERE name = %s AND group_id = %s", (instance_name, group_id))

        db_conn.commit()
        cursor.close()
        db_conn.close()

        await query.message.reply_text(f"Instance '{instance_name}' has been {action}d.")
        context.user_data.clear()

    except Exception as e:
        logging.error(e)

def main():
    application = ApplicationBuilder().token('7059521350:AAE3AFr93t4TA939AfOx9uwxdV0-l5EHXds').build()
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("create", create_instance))
    application.add_handler(CommandHandler("activate", list_instances))
    application.add_handler(CommandHandler("close", list_instances))
    application.add_handler(CommandHandler("getid", get_id))
    application.add_handler(CommandHandler("select_group", select_group))
    
    application.add_handler(CallbackQueryHandler(confirm_transaction, pattern='confirm_transaction'))
    application.add_handler(CallbackQueryHandler(copy_callback, pattern='copy_'))
    application.add_handler(CallbackQueryHandler(instance_callback, pattern='instance_'))
    application.add_handler(CallbackQueryHandler(option_callback, pattern='option_'))
    application.add_handler(CallbackQueryHandler(activate_or_close_callback, pattern='^(activate|close)_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, state_handler))
    application.run_polling()
if __name__ == '__main__':
    main()