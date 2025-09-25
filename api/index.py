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
    return {
        "keyboard": [
            [{"text": "📖 ሱራዎች በጽሁፍ"}, {"text": "🎧 ቃሪዎች በድምጽ"}],
            [{"text": "⚙️ ሌሎች"}],
        ],
        "resize_keyboard": True
    }

def text_menu_keyboard(lang='am'):
    return {
        "keyboard": [
            [{"text": "🕋 ሱራ በቁጥር"}, {"text": "📗 ጁዝ በቁጥር"}],
            [{"text": "🔙 ወደ ኋላ"}]
        ],
        "resize_keyboard": True
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

# --- Database & Telegram Functions ---
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
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-114)።")

def handle_juz_input(chat_id, text, lang):
    try:
        juz_number = int(text)
        if not 1 <= juz_number <= 30: raise ValueError
        response = requests.get(f"{QURAN_API_BASE_URL}/juz/{juz_number}")
        response.raise_for_status()
        data = response.json()['data']
        ayahs = data['ayahs']
        header = f"📗 *Juz' {juz_number}*\n\n"
        full_text = ""
        current_surah_name = ""
        for ayah in ayahs:
            if ayah['surah']['name'] != current_surah_name:
                current_surah_name = ayah['surah']['name']
                full_text += f"\n--- {current_surah_name} ---\n"
            full_text += f"{ayah['numberInSurah']}. {ayah['text']}\n"
        
        for i in range(0, len(full_text), 4096 - len(header)):
            chunk = full_text[i:i + 4096 - len(header)]
            send_telegram_message(chat_id, header + chunk)
            header = ""
    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-30)።")

def handle_reciter_surah_input(chat_id, text, lang, reciter_key):
    try:
        surah_number = int(text)
        if not 1 <= surah_number <= 114: raise ValueError
        
        reciter_info = RECITERS[reciter_key]
        reciter_name = reciter_info['name']
        reciter_identifier = reciter_info['identifier']
        
        padded_surah_number = str(surah_number).zfill(3)
        audio_url = f"https://download.quranicaudio.com/quran/{reciter_identifier}/{padded_surah_number}.mp3"
        
        surah_info_response = requests.get(f"{QURAN_API_BASE_URL}/surah/{surah_number}")
        surah_name_english = surah_info_response.json()['data']['englishName']

        message_text = f"🔗 [{surah_name_english} by {reciter_name}]({audio_url})\n\nከላይ ያለውን ሰማያዊ ሊንክ በመጫን ድምጹን በቀጥታ ማዳመጥ ወይም ማውረድ ይችላሉ።"
        send_telegram_message(chat_id, message_text)
    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, "እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ (1-114)። የድምጽ ፋይሉ ላይገኝ ይችላል።")

def handle_support_input(chat_id, text, lang, user_name, user_id):
    forward_message = f"🆘 *New Support Message*\n\n*From:* {user_name} (ID: `{user_id}`)\n\n*Message:* {text}"
    if ADMIN_ID: send_telegram_message(ADMIN_ID, forward_message)
    send_telegram_message(chat_id, "✅ መልዕክትዎ ለአድሚኑ ተልኳል።")

# --- Admin Handlers ---
def handle_status(chat_id):
    db_data = get_db()
    user_count = len(db_data.get('users', [])) if db_data else 'N/A'
    send_telegram_message(chat_id, f"📊 *Bot Status*\n\nTotal Users: *{user_count}*")

def handle_broadcast(admin_id, text_parts):
    if not text_parts:
        send_telegram_message(admin_id, "Usage: `/broadcast <message>`")
        return
    message_text = " ".join(text_parts)
    db_data = get_db()
    users = db_data.get('users', [])
    sent_count, failed_count = 0, 0
    for user_id in users:
        try:
            send_telegram_message(user_id, message_text)
            sent_count += 1
            time.sleep(0.1)
        except Exception:
            failed_count += 1
    send_telegram_message(admin_id, f"✅ Broadcast sent to {sent_count} users.\n❌ Failed to send to {failed_count} users.")

# --- Main Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # Handle inline button clicks for language
    if 'callback_query' in update:
        callback_query = update['callback_query']
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            user_languages[chat_id] = lang_code
            send_telegram_message(chat_id, f"✅ Language changed to {lang_code.upper()}.")
        return 'ok'

    if 'message' not in update:
        return 'ok'

    message = update['message']
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    user_name = message['from'].get('first_name', 'User')
    text = message.get('text', '')
    lang = get_user_lang(chat_id)
    is_admin = str(user_id) == ADMIN_ID
    
    if text.startswith('/'):
        command_parts = text.split()
        command = command_parts[0]
        args = command_parts[1:]
        if command == '/start':
            add_user_to_db(user_id)
            user_state.pop(chat_id, None)
            send_telegram_message(chat_id, "እባክዎ ከታች ካሉት ምናሌዎች ይምረጡ:", reply_markup=main_menu_keyboard(lang))
            return 'ok'
        elif is_admin and command == '/status':
            handle_status(chat_id)
            return 'ok'
        elif is_admin and command == '/broadcast':
            handle_broadcast(chat_id, args)
            return 'ok'

    if not is_admin and not is_user_member(user_id):
        if user_id in member_cache: member_cache.pop(user_id)
        channel_name = CHANNEL_ID.replace('@', '') if CHANNEL_ID else ''
        keyboard = {"inline_keyboard": [[{"text": "✅ please first join channel", "url": f"https://t.me/{channel_name}"}]]}
        send_telegram_message(chat_id, "🙏 ቦቱን ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ።", reply_markup=keyboard)
        return 'ok'

    current_state_info = user_state.get(chat_id)
    if current_state_info:
        state = current_state_info.get('state')
        if state == 'awaiting_surah': handle_surah_input(chat_id, text, lang)
        elif state == 'awaiting_juz': handle_juz_input(chat_id, text, lang)
        elif state == 'awaiting_surah_for_reciter': handle_reciter_surah_input(chat_id, text, lang, current_state_info.get('reciter'))
        elif state == 'awaiting_support_message': handle_support_input(chat_id, text, lang, user_name, user_id)
        
        user_state.pop(chat_id, None)
        send_telegram_message(chat_id, "ዋና ምናሌ:", reply_markup=main_menu_keyboard(lang))
        return 'ok'

    if text == "📖 ሱራዎች በጽሁፍ":
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
        keyboard = {"inline_keyboard": [[{"text": "አማርኛ", "callback_data": "set_lang_am"}, {"text": "English", "callback_data": "set_lang_en"}],[{"text": "العربية", "callback_data": "set_lang_ar"}, {"text": "Türkçe", "callback_data": "set_lang_tr"}]]}
        send_telegram_message(chat_id, "እባክዎ ቋንቋ ይምረጡ:", reply_markup=keyboard)
    elif text == "🆘 እርዳታ":
        user_state[chat_id] = {'state': 'awaiting_support_message'}
        send_telegram_message(chat_id, "እባክዎ የመልዕክትዎን ይዘት ይላኩ። ለአድሚኑ ይደርሳል።", reply_markup={"remove_keyboard": True})
    elif text == '🔙 ወደ ኋላ':
        send_telegram_message(chat_id, "ዋና ምናሌ:", reply_markup=main_menu_keyboard(lang))
    
    return 'ok'

@app.route('/')
def index():
    return "Quran Bot with Button Menu is running!"
