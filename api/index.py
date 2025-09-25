import os
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

# የተጠቃሚ መረጃን (state) እና የቋንቋ ምርጫን ለጊዜው ለማስቀመጥ
user_state = {}
user_languages = {}
member_cache = {}

# --- Menu Keyboards ---
def main_menu_keyboard(lang='am'):
    # This can be localized later if needed
    return {
        "keyboard": [
            [{"text": "📖 ሱራዎች በጽሁፍ"}, {"text": "🎧 ቃሪዎች በድምጽ"}],
            [{"text": "⚙️ ሌሎች"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def text_menu_keyboard(lang='am'):
    return {
        "keyboard": [
            [{"text": "🕋 ሱራ በቁጥር"}, {"text": "📗 ጁዝ በቁጥር"}],
            [{"text": "🔙 ወደ ኋላ"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
def reciters_menu_keyboard(lang='am'):
    keyboard = []
    for key, value in RECITERS.items():
        keyboard.append([{"text": value['name']}])
    keyboard.append([{"text": "🔙 ወደ ኋላ"}])
    return {"keyboard": keyboard, "resize_keyboard": True}

def other_menu_keyboard(lang='am'):
     return {
        "keyboard": [
            [{"text": "🌐 ቋንቋ"}, {"text": "🆘 እርዳታ"}],
            [{"text": "🔙 ወደ ኋላ"}]
        ],
        "resize_keyboard": True
    }

# --- Database & Telegram Functions (No changes needed) ---
def get_db():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return None
    headers = {'X-Master-Key': JSONBIN_API_KEY, 'X-Bin-Meta': 'false'}
    try:
        req = requests.get(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', headers=headers, timeout=10)
        req.raise_for_status()
        return req.json()
    except requests.RequestException:
        return None

def update_db(data):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return False
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        req = requests.put(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', json=data, headers=headers, timeout=10)
        req.raise_for_status()
        return True
    except requests.RequestException:
        return False

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
        data = response.json()['data']
        surah_name = data['englishName']
        ayahs = data['ayahs']
        message = f"🕋 *Surah {surah_number}: {surah_name}*\n\n"
        full_text = ""
        for ayah in ayahs:
            full_text += f"{ayah['numberInSurah']}. {ayah['text']}\n"
        
        for i in range(0, len(full_text), 4096):
            send_telegram_message(chat_id, message + full_text[i:i+4096])
            message = "" # Only send header with the first part
    except (ValueError, KeyError):
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-114)።")

def handle_juz_input(chat_id, text, lang):
    try:
        juz_number = int(text)
        # Fetch and send Juz text...
        send_telegram_message(chat_id, f"Fetching Juz {juz_number}...")
    except ValueError:
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-30)።")

def handle_reciter_surah_input(chat_id, text, lang, reciter_key):
    try:
        surah_number = int(text)
        # Fetch and send recitation link...
        send_telegram_message(chat_id, f"Fetching Surah {surah_number} for {reciter_key}...")
    except ValueError:
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-114)።")

def handle_support_input(chat_id, text, lang, user_name, user_id):
    forward_message = f"🆘 *New Support Message*\n\n*From:* {user_name} (ID: `{user_id}`)\n\n*Message:* {text}"
    if ADMIN_ID: send_telegram_message(ADMIN_ID, forward_message)
    send_telegram_message(chat_id, "✅ መልዕክትዎ ለአድሚኑ ተልኳል።")

# --- Main Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'message' not in update:
        return 'ok'

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    user_name = message['from'].get('first_name', 'User')
    text = message.get('text', '')
    lang = get_user_lang(chat_id)
    is_admin = str(user_id) == ADMIN_ID
    
    if text == '/start':
        add_user_to_db(user_id)
        user_state.pop(chat_id, None)

    if not is_admin and not is_user_member(user_id):
        if user_id in member_cache: member_cache.pop(user_id)
        channel_name = CHANNEL_ID.replace('@', '') if CHANNEL_ID else ''
        keyboard = {"inline_keyboard": [[{"text": "✅ please first join channel", "url": f"https://t.me/{channel_name}"}]]}
        send_telegram_message(chat_id, "🙏 ቦቱን ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ።", reply_markup=keyboard)
        return 'ok'

    current_state_info = user_state.get(chat_id)

    if current_state_info:
        state = current_state_info.get('state')
        if state == 'awaiting_surah':
            handle_surah_input(chat_id, text, lang)
        elif state == 'awaiting_juz':
            handle_juz_input(chat_id, text, lang)
        elif state == 'awaiting_surah_for_reciter':
            handle_reciter_surah_input(chat_id, text, lang, current_state_info.get('reciter'))
        elif state == 'awaiting_support_message':
            handle_support_input(chat_id, text, lang, user_name, user_id)
        
        user_state.pop(chat_id, None)
        send_telegram_message(chat_id, "ዋና ምናሌ:", reply_markup=main_menu_keyboard(lang))
        return 'ok'

    if text == '/start' or text == '🔙 ወደ ኋላ':
        send_telegram_message(chat_id, "እባክዎ ከታች ካሉት ምናሌዎች ይምረጡ:", reply_markup=main_menu_keyboard(lang))
    
    elif text == "📖 ሱራዎች በጽሁፍ":
        send_telegram_message(chat_id, "ሱራ ይፈልጋሉ ወይስ ጁዝ?", reply_markup=text_menu_keyboard(lang))
    
    elif text == "🎧 ቃሪዎች በድምጽ":
        send_telegram_message(chat_id, "እባክዎ የሚፈልጉትን ቃሪዕ ይምረጡ:", reply_markup=reciters_menu_keyboard(lang))

    elif text == "⚙️ ሌሎች":
        send_telegram_message(chat_id, "ሌሎች አገልግሎቶች:", reply_markup=other_menu_keyboard(lang))

    elif text == "🕋 ሱራ በቁጥር":
        user_state[chat_id] = {'state': 'awaiting_surah'}
        send_telegram_message(chat_id, "እባክዎ የሚፈልጉትን የሱራ ቁጥር ብቻ ይላኩ።", reply_markup={"remove_keyboard": True})

    elif text == "📗 ጁዝ በቁጥር":
        user_state[chat_id] = {'state': 'awaiting_juz'}
        send_telegram_message(chat_id, "እባክዎ የሚፈልጉትን የጁዝ ቁጥር ብቻ ይላኩ።", reply_markup={"remove_keyboard": True})
        
    elif text in [value['name'] for value in RECITERS.values()]:
        reciter_key = next((key for key, value in RECITERS.items() if value['name'] == text), None)
        if reciter_key:
            user_state[chat_id] = {'state': 'awaiting_surah_for_reciter', 'reciter': reciter_key}
            send_telegram_message(chat_id, f"ለ *{text}* የትኛውን ሱራ መስማት ይፈልጋሉ? እባክዎ የሱራውን ቁጥር ብቻ ይላኩ።", reply_markup={"remove_keyboard": True})
    
    elif text == "🌐 ቋንቋ":
        # This part remains inline as it's better UX
        keyboard = {"inline_keyboard": [[{"text": "አማርኛ", "callback_data": "set_lang_am"}, {"text": "English", "callback_data": "set_lang_en"}],[{"text": "العربية", "callback_data": "set_lang_ar"}, {"text": "Türkçe", "callback_data": "set_lang_tr"}]]}
        send_telegram_message(chat_id, "እባክዎ ቋንቋ ይምረጡ:", reply_markup=keyboard)

    elif text == "🆘 እርዳታ":
        user_state[chat_id] = {'state': 'awaiting_support_message'}
        send_telegram_message(chat_id, "እባክዎ የመልዕክትዎን ይዘት ይላኩ። ለአድሚኑ ይደርሳል።", reply_markup={"remove_keyboard": True})

    # Admin commands remain as text commands
    elif is_admin and text == '/status':
        # ... handle_status call ...
        pass
    
    return 'ok'

@app.route('/')
def index():
    return "Quran Bot with Button Menu is running!"
v
