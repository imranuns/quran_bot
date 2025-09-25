import os
import os
import requests
import json
from flask import Flask, request
import time
import random

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

# የተጠቃሚ መረጃን (state) እና የቋንቋ ምርጫን ለጊዜው ለማስቀመጥ
user_state = {}
user_languages = {}
member_cache = {}


# --- Multi-language Messages and Buttons ---
MESSAGES = {
    'am': {
        "welcome": "🕌 Assalamu Alaikum {username}\n\n📖 ወደ ቁርአን ቦት በደህና መጡ!",
        "main_menu_prompt": "እባክዎ ከታች ካሉት ምናሌዎች ይምረጡ:",
        "back_to_main": "ዋና ምናሌ:",
        "select_reciter": "እባክዎ የሚፈልጉትን ቃሪዕ ይምረጡ:",
        "select_text_type": "ሱራ ይፈልጋሉ ወይስ ጁዝ?",
        "other_options": "ሌሎች አገልግሎቶች:",
        "request_surah_number": "እባክዎ የሚፈልጉትን የሱራ ቁጥር ብቻ ይላኩ።",
        "request_juz_number": "እባክዎ የሚፈልጉትን የጁዝ ቁጥር ብቻ ይላኩ።",
        "request_reciter_surah": "ለ *{reciter_name}* የትኛውን ሱራ መስማት ይፈልጋሉ? እባክዎ የሱራውን ቁጥር ብቻ ይላኩ።",
        "request_support_message": "እባክዎ የመልዕክትዎን ይዘት ይላኩ። ለአድሚኑ ይደርሳል።",
        "language_prompt": "እባክዎ ቋንቋ ይምረጡ:",
        "language_selected": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል።",
        "support_sent": "✅ መልዕክትዎ ለአድሚኑ ተልኳል።",
        "force_join": "🙏 ቦቱን ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ።",
        "join_button_text": "✅ please first join channel",
        "invalid_number": "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ።",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nከላይ ያለውን ሰማያዊ ሊንክ በመጫን ድምጹን በቀጥታ ማዳመጥ ወይም ማውረድ ይችላሉ።",
        "fetching_ayah": "📖 የቀኑን አያ በማዘጋጀት ላይ ነው... እባክዎ ትንሽ ይጠብቁ።",
        "buttons": {
            "surah_text": "📖 ሱራዎች በጽሁፍ", "reciters_audio": "🎧 ቃሪዎች በድምጽ",
            "other": "⚙️ ሌሎች", "back": "🔙 ወደ ኋላ",
            "surah_by_number": "🕋 ሱራ በቁጥር", "juz_by_number": "📗 ጁዝ በቁጥር",
            "language": "🌐 ቋንቋ", "support": "🆘 እርዳታ",
            "daily_ayah": "📖 የቀኑ አያ"
        }
    },
    'en': {
        "welcome": "🕌 Assalamu Alaikum {username}\n\n📖 Welcome to the Quran Bot!",
        "main_menu_prompt": "Please choose from the menu below:",
        "back_to_main": "Main Menu:",
        "select_reciter": "Please select a reciter:",
        "select_text_type": "Do you want a Surah or a Juz?",
        "other_options": "Other services:",
        "request_surah_number": "Please send the Surah number you want.",
        "request_juz_number": "Please send the Juz' number you want.",
        "request_reciter_surah": "Which Surah would you like to hear from *{reciter_name}*? Please send the Surah number.",
        "request_support_message": "Please send your message content. It will be forwarded to the admin.",
        "language_prompt": "Please select a language:",
        "language_selected": "✅ Language changed to English.",
        "support_sent": "✅ Your message has been sent to the admin.",
        "force_join": "🙏 To use the bot, please join our channel first.",
        "join_button_text": "✅ please first join channel",
        "invalid_number": "Please enter a valid number.",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nYou can listen or download by clicking the link above.",
        "fetching_ayah": "📖 Fetching the Verse of the Day... Please wait.",
        "buttons": {
            "surah_text": "📖 Surahs in Text", "reciters_audio": "🎧 Reciters by Audio",
            "other": "⚙️ Others", "back": "🔙 Back",
            "surah_by_number": "🕋 Surah by Number", "juz_by_number": "📗 Juz by Number",
            "language": "🌐 Language", "support": "🆘 Support",
            "daily_ayah": "📖 Verse of the Day"
        }
    },
    # Add 'ar' and 'tr' dictionaries here in the same format
}


# --- Menu Keyboards (Now Dynamic) ---
def main_menu_keyboard(lang='am'):
    buttons = MESSAGES.get(lang, MESSAGES['am'])['buttons']
    return {
        "keyboard": [
            [{"text": buttons['surah_text']}, {"text": buttons['reciters_audio']}],
            [{"text": buttons['other']}],
        ], "resize_keyboard": True
    }

def text_menu_keyboard(lang='am'):
    buttons = MESSAGES.get(lang, MESSAGES['am'])['buttons']
    return {
        "keyboard": [
            [{"text": buttons['surah_by_number']}, {"text": buttons['juz_by_number']}],
            [{"text": buttons['back']}]
        ], "resize_keyboard": True
    }
    
def reciters_menu_keyboard(lang='am'):
    buttons = MESSAGES.get(lang, MESSAGES['am'])['buttons']
    keyboard = []
    for key, value in RECITERS.items():
        keyboard.append([{"text": value['name']}])
    keyboard.append([{"text": buttons['back']}])
    return {"keyboard": keyboard, "resize_keyboard": True}

def other_menu_keyboard(lang='am'):
    buttons = MESSAGES.get(lang, MESSAGES['am'])['buttons']
    return {
        "keyboard": [
            [{"text": buttons['language']}, {"text": buttons['support']}],
            [{"text": buttons['daily_ayah']}],
            [{"text": buttons['back']}]
        ], "resize_keyboard": True
    }

# --- Database & Telegram Functions (No changes needed) ---
def get_db():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return None
    headers = {'X-Master-Key': JSONBIN_API_KEY, 'X-Bin-Meta': 'false'}
    try:
        req = requests.get(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', headers=headers, timeout=10)
        req.raise_for_status()
        return req.json()
    except requests.RequestException: return None

def update_db(data):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return False
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        req = requests.put(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', json=data, headers=headers, timeout=10)
        req.raise_for_status()
        return True
    except requests.RequestException: return False

def add_user_to_db(user_id):
    db_data = get_db()
    if db_data is None: return
    users = db_data.get('users', [])
    if user_id not in users:
        users.append(user_id)
        db_data['users'] = users
        update_db(db_data)
        
def send_telegram_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def get_user_lang(chat_id):
    return user_languages.get(chat_id, 'am')

def is_user_member(user_id):
    if user_id in member_cache and (time.time() - member_cache[user_id]['timestamp'] < 300):
        return member_cache[user_id]['is_member']
    if not CHANNEL_ID: return True
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
        payload = {'chat_id': CHANNEL_ID, 'user_id': user_id}
        response = requests.get(url, params=payload, timeout=5)
        data = response.json()
        if data.get('ok'):
            status = data['result']['status']
            is_member = status in ['creator', 'administrator', 'member']
            member_cache[user_id] = {'is_member': is_member, 'timestamp': time.time()}
            return is_member
    except Exception: return False
    return False

# --- Handlers for user input based on state ---
def handle_surah_input(chat_id, text, lang):
    try:
        surah_number = int(text)
        if not 1 <= surah_number <= 114: raise ValueError
        response = requests.get(f"{QURAN_API_BASE_URL}/surah/{surah_number}")
        response.raise_for_status()
        data = response.json()['data']
        surah_name = data['englishName']
        ayahs = data['ayahs']
        header = f"🕋 *Surah {surah_number}: {surah_name}*\n\n"
        full_text = ""
        for ayah in ayahs:
            full_text += f"{ayah['numberInSurah']}. {ayah['text']}\n"
        
        for i in range(0, len(full_text), 4096 - len(header)):
            chunk = full_text[i:i + 4096 - len(header)]
            send_telegram_message(chat_id, header + chunk)
            header = ""
    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["invalid_number"])

def handle_juz_input(chat_id, text, lang):
    # ... (Implementation is the same as the previous full version)
    pass

def handle_reciter_surah_input(chat_id, text, lang, reciter_key):
    # ... (Implementation is the same as the previous full version)
    pass

def handle_support_input(chat_id, text, lang, user_name, user_id):
    # ... (Implementation is the same as the previous full version)
    pass
    
def handle_daily_ayah(chat_id, lang):
    try:
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])['fetching_ayah'])
        # A random number from 1 to 6236 (total ayahs in Quran)
        random_ayah_number = random.randint(1, 6236)
        response = requests.get(f"{QURAN_API_BASE_URL}/ayah/{random_ayah_number}")
        response.raise_for_status()
        data = response.json()['data']
        
        ayah_text = data['text']
        surah_name = data['surah']['englishName']
        ayah_in_surah = data['numberInSurah']
        
        message = f"📖 *Verse of the Day*\n\n`{ayah_text}`\n\n- {surah_name}, Verse {ayah_in_surah}"
        send_telegram_message(chat_id, message)
    except requests.RequestException as e:
        print(f"Error fetching daily ayah: {e}")
        send_telegram_message(chat_id, "Sorry, could not fetch the verse of the day at this moment.")


# --- Admin Handlers ---
def handle_status(chat_id):
    #... (Implementation is the same as the previous full version)
    pass
def handle_broadcast(admin_id, text_parts):
    # ... (Implementation is the same as the previous full version)
    pass

# --- Main Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # Handle inline button clicks for language
    if 'callback_query' in update:
        # ... (Implementation is the same)
        pass

    if 'message' not in update:
        return 'ok'

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    user_name = message['from'].get('first_name', 'User')
    text = message.get('text', '')
    lang = get_user_lang(chat_id)
    buttons = MESSAGES.get(lang, MESSAGES['am'])['buttons']
    is_admin = str(user_id) == ADMIN_ID
    
    if text.startswith('/'):
        # ... (Implementation is the same)
        pass

    if not is_admin and not is_user_member(user_id):
        # ... (Implementation is the same)
        pass

    current_state_info = user_state.get(chat_id)
    if current_state_info:
        # ... (Implementation is the same)
        pass

    # --- Button Text Handling (Now Dynamic) ---
    if text == buttons['surah_text']:
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["select_text_type"], reply_markup=text_menu_keyboard(lang))
    elif text == buttons['reciters_audio']:
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["select_reciter"], reply_markup=reciters_menu_keyboard(lang))
    elif text == buttons['other']:
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["other_options"], reply_markup=other_menu_keyboard(lang))
    
    elif text == buttons['daily_ayah']:
        handle_daily_ayah(chat_id, lang)

    elif text == buttons['surah_by_number']:
        user_state[chat_id] = {'state': 'awaiting_surah'}
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["request_surah_number"], reply_markup={"remove_keyboard": True})
    
    # ... (Rest of the button handlers are the same)
    
    elif text == buttons['back']:
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["back_to_main"], reply_markup=main_menu_keyboard(lang))
    
    return 'ok'

@app.route('/')
def index():
    return "Quran Bot with Daily Ayah feature is running!"
