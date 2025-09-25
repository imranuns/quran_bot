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
    'abdulbasit': {'name': 'Al-Sheikh Abdul basit Abdul Samad', 'identifier': 'Abdul_Basit_Murattal_64kbps'},
    'yasser': {'name': 'Reader Yasser Al-Dosari', 'identifier': 'Yasser_Ad-Dussary_128kbps'},
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
        "request_surah_number": "🕋 ሱራ በቁጥር\n\nእባክዎ የሚፈልጉትን የሱራ ቁጥር ብቻ ይላኩ።",
        "request_juz_number": "📗 ጁዝ በቁጥር\n\nእባክዎ የሚፈልጉትን የጁዝ ቁጥር ብቻ ይላኩ።",
        "request_reciter_surah": "{reciter_name}\n\nለ {reciter_name} የትኛውን ሱራ መስማት ይፈልጋሉ? እባክዎ የሱራውን ቁጥር ብቻ ይላኩ።",
        "request_support_message": "እባክዎ የመልዕክትዎን ይዘት ይላኩ። ለአድሚኑ ይደርሳል።",
        "language_prompt": "እባክዎ ቋንቋ ይምረጡ:",
        "language_selected": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል።",
        "support_sent": "✅ መልዕክትዎ ለአድሚኑ ተልኳል።",
        "force_join": "🙏 ቦቱን ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ።",
        "join_button_text": "✅ please first join channel",
        "invalid_number": "❌ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ።",
        "fetching_data": "⏳ በማዘጋጀት ላይ ነው... እባክዎ ትንሽ ይጠብቁ።",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nከላይ ያለውን ሰማያዊ ሊንክ በመጫን ድምጹን በቀጥታ ማዳመጥ ወይም ማውረድ ይችላሉ።",
        "error_fetching": "ይቅርታ፣ የድምጽ ፋይሉን ሊንክ ማግኘት አልቻልኩም።\n\n**ምክንያት:** የድምጽ ፋይሉ በድረ-ገጹ ላይ አልተገኘም (404 Error)።\n**የተሞከረው ሊንክ:** `{full_audio_url}`",
        "buttons": {
            "surah_text": "📖 ሱራዎች በጽሁፍ", "reciters_audio": "🎧 ቃሪዎች በድምጽ",
            "other": "⚙️ ሌሎች", "back": "🔙 ወደ ኋላ",
            "surah_by_number": "🕋 ሱራ በቁጥር", "juz_by_number": "📗 ጁዝ በቁጥር",
            "language": "🌐 ቋንቋ", "support": "🆘 እርዳታ"
        }
    },
    'en': {
        "welcome": "🕌 Assalamu Alaikum {username}\n\n📖 Welcome to the Quran Bot!",
        "main_menu_prompt": "Please choose from the menu below:",
        "back_to_main": "Main Menu:",
        "select_reciter": "Please select a reciter:",
        "select_text_type": "Do you want a Surah or a Juz?",
        "other_options": "Other services:",
        "request_surah_number": "🕋 Surah by Number\n\nPlease send the Surah number you want.",
        "request_juz_number": "📗 Juz by Number\n\nPlease send the Juz' number you want.",
        "request_reciter_surah": "{reciter_name}\n\nWhich Surah would you like to hear from *{reciter_name}*? Please send the Surah number.",
        "request_support_message": "Please send your message content. It will be forwarded to the admin.",
        "language_prompt": "Please select a language:",
        "language_selected": "✅ Language changed to English.",
        "support_sent": "✅ Your message has been sent to the admin.",
        "force_join": "🙏 To use the bot, please join our channel first.",
        "join_button_text": "✅ please first join channel",
        "invalid_number": "❌ Please enter a valid number.",
        "fetching_data": "⏳ Fetching data... Please wait.",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nYou can listen or download by clicking the link above.",
        "error_fetching": "Sorry, I could not get the audio link.\n\n**Reason:** The audio file was not found on the server (404 Error).\n**Attempted Link:** `{full_audio_url}`",
        "buttons": {
            "surah_text": "📖 Surahs in Text", "reciters_audio": "🎧 Reciters by Audio",
            "other": "⚙️ Others", "back": "🔙 Back",
            "surah_by_number": "🕋 Surah by Number", "juz_by_number": "📗 Juz by Number",
            "language": "🌐 Language", "support": "🆘 Support"
        }
    },
    'ar': {
        "welcome": "🕌 السلام عليكم {username}\n\n📖 أهلاً بك في بوت القرآن!",
        "main_menu_prompt": "يرجى الاختيار من القائمة أدناه:",
        "back_to_main": "القائمة الرئيسية:",
        "select_reciter": "يرجى اختيار القارئ:",
        "select_text_type": "هل تريد سورة أم جزء؟",
        "other_options": "خدمات أخرى:",
        "request_surah_number": "🕋 سورة برقم\n\nيرجى إرسال رقم السورة الذي تريده.",
        "request_juz_number": "📗 جزء برقم\n\nيرجى إرسال رقم الجزء الذي تريده.",
        "request_reciter_surah": "{reciter_name}\n\nأي سورة تود سماعها من *{reciter_name}*؟ يرجى إرسال رقم السورة.",
        "request_support_message": "يرجى إرسال محتوى رسالتك. سيتم توجيهها إلى المسؤول.",
        "language_prompt": "يرجى اختيار اللغة:",
        "language_selected": "✅ تم تغيير اللغة إلى العربية.",
        "support_sent": "✅ تم إرسال رسالتك إلى المسؤول.",
        "force_join": "🙏 لاستخدام البوت، يرجى الانضمام إلى قناتنا أولاً.",
        "join_button_text": "✅ يرجى الانضمام للقناة أولاً",
        "invalid_number": "❌ يرجى إدخال رقم صحيح.",
        "fetching_data": "⏳ جاري جلب البيانات... يرجى الانتظار قليلاً.",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nيمكنك الاستماع أو التنزيل بالنقر على الرابط أعلاه.",
        "error_fetching": "عذراً، لم أتمكن من الحصول على رابط الصوت.\n\n**السبب:** لم يتم العثور على الملف الصوتي على الخادم (خطأ 404).\n**الرابط الذي تمت محاولته:** `{full_audio_url}`",
        "buttons": {
            "surah_text": "📖 سور كنص", "reciters_audio": "🎧 قراء بالصوت",
            "other": "⚙️ أخرى", "back": "🔙 رجوع",
            "surah_by_number": "🕋 سورة برقم", "juz_by_number": "📗 جزء برقم",
            "language": "🌐 اللغة", "support": "🆘 مساعدة"
        }
    },
    'tr': {
        "welcome": "🕌 Selamun Aleykum {username}\n\n📖 Kur'an Bot'a hoş geldiniz!",
        "main_menu_prompt": "Lütfen aşağıdaki menüden seçim yapın:",
        "back_to_main": "Ana Menü:",
        "select_reciter": "Lütfen bir okuyucu seçin:",
        "select_text_type": "Sure mi yoksa Cüz mü istersiniz?",
        "other_options": "Diğer hizmetler:",
        "request_surah_number": "🕋 Numaraya Göre Sure\n\nLütfen istediğiniz Sure numarasını gönderin.",
        "request_juz_number": "📗 Numaraya Göre Cüz\n\nLütfen istediğiniz Cüz numarasını gönderin.",
        "request_reciter_surah": "{reciter_name}\n\n*{reciter_name}* adlı okuyucudan hangi Sureyi dinlemek istersiniz? Lütfen Sure numarasını gönderin.",
        "request_support_message": "Lütfen mesajınızın içeriğini gönderin. Yöneticiye iletilecektir.",
        "language_prompt": "Lütfen bir dil seçin:",
        "language_selected": "✅ Dil Türkçe olarak değiştirildi.",
        "support_sent": "✅ Mesajınız yöneticiye gönderildi.",
        "force_join": "🙏 Botu kullanmak için lütfen önce kanalımıza katılın.",
        "join_button_text": "✅ lütfen önce kanala katılın",
        "invalid_number": "❌ Lütfen geçerli bir numara girin.",
        "fetching_data": "⏳ Veriler alınıyor... Lütfen bekleyin.",
        "audio_link_message": "🔗 [{surah_name} by {reciter_name}]({audio_url})\n\nYukarıdaki bağlantıya tıklayarak dinleyebilir veya indirebilirsiniz.",
        "error_fetching": "Üzgünüm, ses bağlantısını alamadım.\n\n**Sebep:** Ses dosyası sunucuda bulunamadı (404 Hatası).\n**Denenen Bağlantı:** `{full_audio_url}`",
        "buttons": {
            "surah_text": "📖 Metin Olarak Sureler", "reciters_audio": "🎧 Sesli Okuyucular",
            "other": "⚙️ Diğer", "back": "🔙 Geri",
            "surah_by_number": "🕋 Numaraya Göre Sure", "juz_by_number": "📗 Numaraya Göre Cüz",
            "language": "🌐 Dil", "support": "🆘 Destek"
        }
    }
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
            [{"text": buttons['back']}]
        ], "resize_keyboard": True
    }

# --- Database & Telegram Functions ---
def get_db():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return None
    headers = {'X-Master-Key': JSONBIN_API_KEY, 'X-Bin-Meta': 'false'}
    try:
        req = requests.get(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', headers=headers, timeout=10)
        req.raise_for_status()
        return req.json()
    except requests.RequestException as e:
        print(f"Error getting DB: {e}")
        return None

def update_db(data):
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return False
    headers = {'Content-Type': 'application/json', 'X-Master-Key': JSONBIN_API_KEY}
    try:
        req = requests.put(f'https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}', json=data, headers=headers, timeout=10)
        req.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Error updating DB: {e}")
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
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False
    return False

# --- Handlers for user input based on state ---
def handle_surah_input(chat_id, text, lang):
    try:
        surah_number = int(text)
        if not 1 <= surah_number <= 114: raise ValueError
        
        send_telegram_message(chat_id, MESSAGES[lang]["fetching_data"])
        
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
            send_telegram_message(chat_id, header + chunk, reply_markup=main_menu_keyboard(lang))
            header = "" # Clear header for subsequent chunks
    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["invalid_number"])

def handle_juz_input(chat_id, text, lang):
    try:
        juz_number = int(text)
        if not 1 <= juz_number <= 30: raise ValueError

        send_telegram_message(chat_id, MESSAGES[lang]["fetching_data"])
        
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
            send_telegram_message(chat_id, header + chunk, reply_markup=main_menu_keyboard(lang))
            header = ""
    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["invalid_number"])


def handle_reciter_surah_input(chat_id, text, lang, reciter_key):
    full_audio_url = ""
    try:
        surah_number = int(text)
        if not 1 <= surah_number <= 114: raise ValueError
        
        send_telegram_message(chat_id, MESSAGES[lang]["fetching_data"])

        reciter_info = RECITERS[reciter_key]
        reciter_name = reciter_info['name']
        reciter_identifier = reciter_info['identifier']
        
        # We need the Surah name for the link text
        surah_info_response = requests.get(f"https://api.quran.com/api/v4/chapters/{surah_number}")
        surah_info_response.raise_for_status()
        surah_name_english = surah_info_response.json()['chapter']['name_simple']
        
        padded_surah_number = str(surah_number).zfill(3)
        full_audio_url = f"https://download.quranicaudio.com/quran/{reciter_identifier}/{padded_surah_number}.mp3"
        
        message_text = MESSAGES[lang]["audio_link_message"].format(surah_name=surah_name_english, reciter_name=reciter_name, audio_url=full_audio_url)
        send_telegram_message(chat_id, message_text, reply_markup=main_menu_keyboard(lang))

    except (ValueError, KeyError, requests.RequestException):
        send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['am'])["invalid_number"])

def handle_support_input(chat_id, text, lang, user_name, user_id):
    support_message = f"🆘 *New Support Message*\n\n*From:* {user_name} (ID: `{user_id}`)\n\n*Message:* {text}"
    if ADMIN_ID: send_telegram_message(ADMIN_ID, support_message)
    send_telegram_message(chat_id, MESSAGES[lang]["support_sent"], reply_markup=main_menu_keyboard(lang))

# --- Admin Handlers ---
def handle_status(chat_id):
    db_data = get_db()
    if db_data is not None:
        user_count = len(db_data.get('users', []))
        send_telegram_message(chat_id, f"📊 *Bot Status*\n\nTotal Users: *{user_count}*")
    else:
        send_telegram_message(chat_id, "❌ Could not get status. DB connection failed.")

def handle_broadcast(admin_id, text_parts):
    if not text_parts:
        send_telegram_message(admin_id, "Please provide a message to broadcast.")
        return
    
    broadcast_text = " ".join(text_parts)
    db_data = get_db()
    if db_data is None:
        send_telegram_message(admin_id, "❌ Broadcast failed. DB connection failed.")
        return

    users = db_data.get('users', [])
    sent_count = 0
    failed_count = 0
    for user_id in users:
        try:
            send_telegram_message(user_id, broadcast_text)
            sent_count += 1
            time.sleep(0.1) 
        except Exception:
            failed_count += 1
    send_telegram_message(admin_id, f"✅ Broadcast sent to *{sent_count}* users.\n❌ Failed to send to *{failed_count}* users.")
    
def handle_debug(chat_id):
    report = "*🐞 Debug Report*\n\n"
    report += "*Environment Variables:*\n"
    report += f"- `ADMIN_ID`: {'✅ Set' if ADMIN_ID else '❌ NOT SET'}\n"
    report += f"- `CHANNEL_ID`: {'✅ Set' if CHANNEL_ID else '❌ NOT SET'}\n"
    report += f"- `JSONBIN_API_KEY`: {'✅ Set' if JSONBIN_API_KEY else '❌ NOT SET'}\n"
    report += f"- `JSONBIN_BIN_ID`: {'✅ Set' if JSONBIN_BIN_ID else '❌ NOT SET'}\n\n"
    report += "*JSONBin.io Connection Test:*\n"
    db_data = get_db()
    if db_data is not None:
        report += "✅ Connection Successful!\n"
        report += f"   - Found *{len(db_data.get('users', []))}* users in DB."
    else:
        report += f"❌ Connection Failed!"
    send_telegram_message(chat_id, report)

# --- Main Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # Handle inline button clicks for language
    if 'callback_query' in update:
        callback_query = update['callback_query']
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            user_languages[chat_id] = lang_code
            lang = get_user_lang(chat_id)
            send_telegram_message(chat_id, MESSAGES[lang]["language_selected"])
            send_telegram_message(chat_id, MESSAGES[lang]["back_to_main"], reply_markup=main_menu_keyboard(lang))
        return 'ok'

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
    
    # Handle Commands
    if text.startswith('/'):
        command_parts = text.split()
        command = command_parts[0].lower()
        args = command_parts[1:]
        
        if command == '/start':
            add_user_to_db(user_id)
            send_telegram_message(chat_id, MESSAGES[lang]["welcome"].format(username=user_name))
            send_telegram_message(chat_id, MESSAGES[lang]["main_menu_prompt"], reply_markup=main_menu_keyboard(lang))
            return 'ok'
        elif is_admin and command == '/status':
            handle_status(chat_id)
            return 'ok'
        elif is_admin and command == '/broadcast':
            handle_broadcast(chat_id, args)
            return 'ok'
        elif is_admin and command == '/debug':
            handle_debug(chat_id)
            return 'ok'

    # Check for channel membership
    if not is_admin and not is_user_member(user_id):
        if user_id in member_cache: member_cache.pop(user_id)
        channel_name = CHANNEL_ID.replace('@', '') if CHANNEL_ID else ''
        keyboard = {"inline_keyboard": [[{"text": MESSAGES[lang]["join_button_text"], "url": f"https://t.me/{channel_name}"}]]}
        send_telegram_message(chat_id, MESSAGES[lang]["force_join"], reply_markup=keyboard)
        return 'ok'

    # Handle state-based inputs
    current_state_info = user_state.get(chat_id)
    if current_state_info:
        state = current_state_info.get('state')
        if state == 'awaiting_surah':
            handle_surah_input(chat_id, text, lang)
        elif state == 'awaiting_juz':
            handle_juz_input(chat_id, text, lang)
        elif state == 'awaiting_reciter_surah':
            reciter_key = current_state_info.get('reciter_key')
            handle_reciter_surah_input(chat_id, text, lang, reciter_key)
        elif state == 'awaiting_support':
            handle_support_input(chat_id, text, lang, user_name, user_id)
        user_state.pop(chat_id, None)
        return 'ok'

    # --- Button Text Handling ---
    reciter_key_map = {v['name']: k for k, v in RECITERS.items()}

    if text == buttons['surah_text']:
        send_telegram_message(chat_id, MESSAGES[lang]["select_text_type"], reply_markup=text_menu_keyboard(lang))
    elif text == buttons['reciters_audio']:
        send_telegram_message(chat_id, MESSAGES[lang]["select_reciter"], reply_markup=reciters_menu_keyboard(lang))
    elif text == buttons['other']:
        send_telegram_message(chat_id, MESSAGES[lang]["other_options"], reply_markup=other_menu_keyboard(lang))
    
    elif text == buttons['surah_by_number']:
        user_state[chat_id] = {'state': 'awaiting_surah'}
        send_telegram_message(chat_id, MESSAGES[lang]["request_surah_number"], reply_markup={"remove_keyboard": True})
    elif text == buttons['juz_by_number']:
        user_state[chat_id] = {'state': 'awaiting_juz'}
        send_telegram_message(chat_id, MESSAGES[lang]["request_juz_number"], reply_markup={"remove_keyboard": True})
    
    elif text == buttons['language']:
        keyboard = {"inline_keyboard": [
            [{"text": "አማርኛ", "callback_data": "set_lang_am"}, {"text": "English", "callback_data": "set_lang_en"}],
            [{"text": "العربية", "callback_data": "set_lang_ar"}, {"text": "Türkçe", "callback_data": "set_lang_tr"}]
        ]}
        send_telegram_message(chat_id, MESSAGES[lang]["language_prompt"], reply_markup=keyboard)
    elif text == buttons['support']:
        user_state[chat_id] = {'state': 'awaiting_support'}
        send_telegram_message(chat_id, MESSAGES[lang]["request_support_message"], reply_markup={"remove_keyboard": True})

    elif text in reciter_key_map:
        reciter_key = reciter_key_map[text]
        reciter_name = RECITERS[reciter_key]['name']
        user_state[chat_id] = {'state': 'awaiting_reciter_surah', 'reciter_key': reciter_key}
        send_telegram_message(chat_id, MESSAGES[lang]["request_reciter_surah"].format(reciter_name=reciter_name), reply_markup={"remove_keyboard": True})
    
    elif text == buttons['back']:
        user_state.pop(chat_id, None)
        send_telegram_message(chat_id, MESSAGES[lang]["back_to_main"], reply_markup=main_menu_keyboard(lang))
    
    return 'ok'

@app.route('/')
def index():
    return "Quran Bot is running with a full button menu!"
