import os
import requests
import json
from flask import Flask, request
import time

# Flask መተግበሪያ መፍጠር
app = Flask(__name__)

# --- Environment Variables ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
JSONBIN_API_KEY = os.environ.get('JSONBIN_API_KEY')
JSONBIN_BIN_ID = os.environ.get('JSONBIN_BIN_ID') 

QURAN_API_BASE_URL = 'http://api.alquran.cloud/v1'

# የቃሪዎች ዝርዝር
RECITERS = {
    'abdulbasit': {'name': 'Al-Sheikh Abdul basit Abdul Samad', 'identifier': 'abdul_basit_murattal'},
    'yasser': {'name': 'Reader Saad Al-ghamdi', 'identifier': 'yasser_ad-dussary'},
}

# የተጠቃሚ መረጃን ለጊዜው ለማስቀመጥ
user_state = {} # To track what the user is currently doing
member_cache = {}

# --- Telegram Functions ---
def send_telegram_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

# --- Database Functions ---
def get_db():
    # ... (same as before, omitted for brevity)
    pass
def update_db(data):
    # ... (same as before, omitted for brevity)
    pass
def add_user_to_db(user_id):
    # ... (same as before, omitted for brevity)
    pass

# --- Core Logic ---
def is_user_member(user_id):
    # ... (same as before, omitted for brevity)
    pass

# --- Menu Keyboards ---
def main_menu_keyboard():
    return {
        "keyboard": [
            [{"text": "📖 ሱራዎች በጽሁፍ"}, {"text": "🎧 ቃሪዎች በድምጽ"}],
            [{"text": "⚙️ ሌሎች"}],
        ],
        "resize_keyboard": True
    }

def reciters_menu_keyboard():
    keyboard = []
    for key, value in RECITERS.items():
        keyboard.append([{"text": value['name']}])
    keyboard.append([{"text": "🔙 ወደ ኋላ"}])
    return {"keyboard": keyboard, "resize_keyboard": True}

def text_menu_keyboard():
    return {
        "keyboard": [
            [{"text": "🕋 ሱራ በቁጥር"}, {"text": "📗 ጁዝ በቁጥር"}],
            [{"text": "🔙 ወደ ኋላ"}]
        ],
        "resize_keyboard": True
    }

def other_menu_keyboard():
    # In a real bot, you would have language and support here
    return {
        "keyboard": [
            [{"text": "🔙 ወደ ኋላ"}]
        ],
        "resize_keyboard": True
    }

# --- Text Handlers ---
def handle_surah(chat_id, text):
    try:
        surah_number = int(text)
        # Fetch and send Surah text...
        send_telegram_message(chat_id, f"Fetching Surah {surah_number}...")
    except ValueError:
        send_telegram_message(chat_id, "እባክዎ ቁጥር ብቻ ያስገቡ።")

def handle_reciter_choice(chat_id, reciter_name):
    # Find the reciter key by name
    reciter_key = next((key for key, value in RECITERS.items() if value['name'] == reciter_name), None)
    if reciter_key:
        user_state[chat_id] = {'state': 'awaiting_surah_for_reciter', 'reciter': reciter_key}
        send_telegram_message(chat_id, f"ለ *{reciter_name}* የትኛውን ሱራ መስማት ይፈልጋሉ? እባክዎ የሱራውን ቁጥር ብቻ ይላኩ።")

# --- Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')

        # Add user to DB on first interaction
        if text == '/start':
            add_user_to_db(user_id)
        
        # Force Join Check can be added here
        
        current_state_info = user_state.get(chat_id)

        # Handle state-based inputs
        if current_state_info:
            state = current_state_info.get('state')
            if state == 'awaiting_surah':
                handle_surah(chat_id, text)
                user_state.pop(chat_id, None) # Clear state
            elif state == 'awaiting_surah_for_reciter':
                # Handle getting surah number for a reciter
                send_telegram_message(chat_id, f"Fetching Surah {text} for reciter {current_state_info.get('reciter')}...")
                user_state.pop(chat_id, None) # Clear state
            return 'ok'

        # Handle regular menu buttons and commands
        if text == '/start':
            send_telegram_message(chat_id, "እባክዎ ከታች ካሉት ምናሌዎች ይምረጡ:", reply_markup=main_menu_keyboard())
        elif text == "📖 ሱራዎች በጽሁፍ":
            send_telegram_message(chat_id, "ሱራ ይፈልጋሉ ወይስ ጁዝ?", reply_markup=text_menu_keyboard())
        elif text == "🎧 ቃሪዎች በድምጽ":
            send_telegram_message(chat_id, "እባክዎ የሚፈልጉትን ቃሪዕ ይምረጡ:", reply_markup=reciters_menu_keyboard())
        elif text == "🕋 ሱራ በቁጥር":
            user_state[chat_id] = {'state': 'awaiting_surah'}
            send_telegram_message(chat_id, "እባክዎ የሚፈልጉትን የሱራ ቁጥር ብቻ ይላኩ።")
        elif text in [value['name'] for value in RECITERS.values()]:
            handle_reciter_choice(chat_id, text)
        elif text == "🔙 ወደ ኋላ":
            user_state.pop(chat_id, None) # Clear any state
            send_telegram_message(chat_id, "ዋና ምናሌ:", reply_markup=main_menu_keyboard())
        elif text == "⚙️ ሌሎች":
             send_telegram_message(chat_id, "ሌሎች አገልግሎቶች በቅርቡ ይታከላሉ።", reply_markup=other_menu_keyboard())
        else:
             if not current_state_info:
                send_telegram_message(chat_id, "ያልታወቀ ትዕዛዝ። እባክዎ ከታች ያሉትን ቁልፎች ይጠቀሙ።", reply_markup=main_menu_keyboard())

    return 'ok'

@app.route('/')
def index():
    return "Quran Bot with Button Menu is running!"
