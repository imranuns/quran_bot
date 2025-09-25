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
    'abdulbasit': {'name': 'Abdul Basit Abdus Samad', 'identifier': 'abdul_basit_murattal'},
    'yasser': {'name': 'Yasser Al-Dosari', 'identifier': 'yasser_ad-dussary'},
}

# የተጠቃሚ ቋንቋ እና የቻናል አባልነት መረጃን ለጊዜው ለማስቀመጥ
user_languages = {}
member_cache = {}

# የቦቱ መልዕክቶች በአራት ቋንቋ
MESSAGES = {
    'am': {
        "welcome": "🕌 Assalamu Alaikum {username}\n\n📖 ወደ ቁርአን ቦት በደህና መጡ!\n\n✍️ ለጽሁፍ የቁርአን አንቀጾች:\n\n/surah <ቁጥር> — ሱራ ቁጥር አስገባ\n/juz <ቁጥር> — ጁዝ ቁጥር አስገባ\n\n🔊 ለድምጽ (ሙሉ ሱራ ሊንክ):\n/abdulbasit <ቁጥር> 🎙️\n/yasser <ቁጥር> 🎧\n\n⚙️ ሌሎች ትዕዛዞች:\n🌐 /language — ቋንቋ ለመቀየር\n🆘 /support <መልዕክት> — ለእርዳታ ለአድሚኑ ይላኩ",
        "language_prompt": "እባክዎ ቋንቋ ይምረጡ:",
        "language_selected": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል።",
        "support_prompt": "እባክዎ ከ `/support` ትዕዛዝ በኋላ መልዕክትዎን ያስገቡ።\nምሳሌ: `/support ሰላም፣ እርዳታ እፈልጋለሁ`",
        "support_sent": "✅ መልዕክትዎ ለአድሚኑ ተልኳል።",
        "force_join": "🙏 ቦቱን ለመጠቀም እባክዎ መጀመሪያ ቻናላችንን ይቀላቀሉ።",
        "join_button_text": "✅ please first join channel",
        "reciter_prompt": "እባክዎ ከቃሪኡ ስም ቀጥሎ የሱራውን ቁጥር ያስገቡ (1-114)።\nአጠቃቀም: `/{reciter_key} 2`",
        "surah_prompt": "እባክዎ ትክክለኛ የሱራ ቁጥር ያስገቡ (1-114)።\nአጠቃቀም: `/surah 2`",
        "juz_prompt": "እባክዎ ትክክለኛ የጁዝ ቁጥር ያስገቡ (1-30)።\nአጠቃቀም: `/juz 15`",
        "audio_link_message": "🔗 [{surah_name_english}]({audio_url})\n\nከላይ ያለውን ሰማያዊ ሊንክ በመጫን ድምጹን በቀጥታ ማዳመጥ ወይም ማውረድ ይችላሉ።",
        "error_fetching": "ይቅርታ፣ የድምጽ ፋይሉን ሊንክ ማግኘት አልቻልኩም።\n\n**ምክንያት:** የድምጽ ፋይሉ በድረ-ገጹ ላይ አልተገኘም (404 Error)።\n**የተሞከረው ሊንክ:** `{full_audio_url}`"
    },
    'en': {
        "welcome": "🕌 Assalamu Alaikum {username}\n\n📖 Welcome to the Quran Bot!\n\n✍️ For Quran verses in text:\n\n/surah <number> — Enter Surah number\n/juz <number> — Enter Juz' number\n\n🔊 For Audio (Full Surah Link):\n/abdulbasit <number> 🎙️\n/yasser <number> 🎧\n\n⚙️ Other Commands:\n🌐 /language — To change language\n🆘 /support <message> — Send a message to the admin for help",
        "language_prompt": "Please select a language:",
        "language_selected": "✅ Language changed to English.",
        "support_prompt": "Please enter your message after the `/support` command.\nExample: `/support Hello, I need help`",
        "support_sent": "✅ Your message has been sent to the admin.",
        "force_join": "🙏 To use the bot, please join our channel first.",
        "join_button_text": "✅ please first join channel",
        "reciter_prompt": "Please provide the Surah number after the reciter's name (1-114).\nUsage: `/{reciter_key} 2`",
        "surah_prompt": "Please provide a valid Surah number (1-114).\nUsage: `/surah 2`",
        "juz_prompt": "Please provide a valid Juz' number (1-30).\nUsage: `/juz 15`",
        "audio_link_message": "🔗 [Download / Play Audio Here]({audio_url})\n\nYou can listen or download the audio by clicking the blue link above.",
        "error_fetching": "Sorry, I could not get the audio link.\n\n**Reason:** The audio file was not found on the server (404 Error).\n**Attempted Link:** `{full_audio_url}`"
    },
    'ar': {
        "welcome": "🕌 السلام عليكم {username}\n\n📖 أهلاً بك في بوت القرآن!\n\n✍️ لآيات القرآن كنص:\n\n/surah <رقم> — أدخل رقم السورة\n/juz <رقم> — أدخل رقم الجزء\n\n🔊 للصوت (رابط السورة كاملة):\n/abdulbasit <رقم> 🎙️\n/yasser <رقم> 🎧\n\n⚙️ أوامر أخرى:\n🌐 /language — لتغيير اللغة\n🆘 /support <رسالة> — أرسل رسالة للمسؤول للمساعدة",
        "language_prompt": "يرجى اختيار اللغة:",
        "language_selected": "✅ تم تغيير اللغة إلى العربية.",
        "support_prompt": "يرجى إدخال رسالتك بعد أمر `/support`.\nمثال: `/support السلام عليكم، أحتاج مساعدة`",
        "support_sent": "✅ تم إرسال رسالتك إلى المسؤول.",
        "force_join": "🙏 لاستخدام البوت، يرجى الانضمام إلى قناتنا أولاً.",
        "join_button_text": "✅ يرجى الانضمام للقناة أولاً",
        "reciter_prompt": "يرجى تقديم رقم السورة بعد اسم القارئ (1-114).\nاستخدام: `/{reciter_key} 2`",
        "surah_prompt": "يرجى تقديم رقم سورة صحيح (1-114).\nاستخدام: `/surah 2`",
        "juz_prompt": "يرجى تقديم رقم جزء صحيح (1-30).\nاستخدام: `/juz 15`",
        "audio_link_message": "🔗 [تنزيل / تشغيل الصوت هنا]({audio_url})\n\nيمكنك الاستماع أو تنزيل الصوت بالنقر على الرابط الأزرق أعلاه.",
        "error_fetching": "عذراً، لم أتمكن من الحصول على رابط الصوت.\n\n**السبب:** لم يتم العثور على الملف الصوتي على الخادم (خطأ 404).\n**الرابط الذي تمت محاولته:** `{full_audio_url}`"
    },
    'tr': {
        "welcome": "🕌 Selamun Aleykum {username}\n\n📖 Kur'an Bot'a hoş geldiniz!\n\n✍️ Metin olarak Kur'an ayetleri için:\n\n/surah <numara> — Sure numarasını girin\n/juz <numara> — Cüz numarasını girin\n\n🔊 Ses için (Tam Sure Bağlantısı):\n/abdulbasit <numara> 🎙️\n/yasser <numara> 🎧\n\n⚙️ Diğer Komutlar:\n🌐 /language — Dili değiştirmek için\n🆘 /support <mesaj> — Yardım için yöneticiye bir mesaj gönderin",
        "language_prompt": "Lütfen bir dil seçin:",
        "language_selected": "✅ Dil Türkçe olarak değiştirildi.",
        "support_prompt": "Lütfen mesajınızı `/support` komutundan sonra girin.\nÖrnek: `/support Merhaba, yardıma ihtiyacım var`",
        "support_sent": "✅ Mesajınız yöneticiye gönderildi.",
        "force_join": "🙏 Botu kullanmak için lütfen önce kanalımıza katılın.",
        "join_button_text": "✅ lütfen önce kanala katılın",
        "reciter_prompt": "Lütfen okuyucunun adından sonra Sure numarasını girin (1-114).\nKullanım: `/{reciter_key} 2`",
        "surah_prompt": "Lütfen geçerli bir Sure numarası girin (1-114).\nKullanım: `/surah 2`",
        "juz_prompt": "Lütfen geçerli bir Cüz numarası girin (1-30).\nKullanım: `/juz 15`",
        "audio_link_message": "🔗 [Sesi İndir / Oynat]({audio_url})\n\nYukarıdaki mavi bağlantıya tıklayarak sesi dinleyebilir veya indirebilirsiniz.",
        "error_fetching": "Üzgünüm, ses bağlantısını alamadım.\n\n**Sebep:** Ses dosyası sunucuda bulunamadı (404 Hatası).\n**Denenen Bağlantı:** `{full_audio_url}`"
    }
}

# --- Database Functions (JSONBin.io) ---
def get_db():
    if not JSONBIN_BIN_ID or not JSONBIN_API_KEY: return {'users': []}
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

# --- Telegram Functions ---
def send_telegram_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=5)
    except requests.exceptions.Timeout:
        pass

def get_user_lang(chat_id):
    return user_languages.get(chat_id, 'am')

def is_user_member(user_id):
    user_info = member_cache.get(user_id)
    if user_info and (time.time() - user_info['timestamp'] < 300): # 5-minute cache
        return user_info['is_member']
    
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

# --- Core Bot Logic Functions ---
def handle_surah(chat_id, args, lang):
    try:
        surah_number = int(args[0])
        if not 1 <= surah_number <= 114: raise ValueError
        response = requests.get(f"{QURAN_API_BASE_URL}/surah/{surah_number}")
        data = response.json()['data']
        surah_name = data['englishName']
        ayahs = data['ayahs']
        message = f"🕋 *Surah {surah_number}: {surah_name}*\n\n"
        for ayah in ayahs:
            message += f"{ayah['numberInSurah']}. {ayah['text']}\n"
        for i in range(0, len(message), 4096):
            send_telegram_message(chat_id, message[i:i+4096])
    except (IndexError, ValueError):
        send_telegram_message(chat_id, MESSAGES[lang]["surah_prompt"])
    except Exception:
        send_telegram_message(chat_id, "Sorry, I could not retrieve the Surah.")

def handle_juz(chat_id, args, lang):
    try:
        juz_number = int(args[0])
        if not 1 <= juz_number <= 30: raise ValueError
        response = requests.get(f"{QURAN_API_BASE_URL}/juz/{juz_number}")
        data = response.json()['data']
        ayahs = data['ayahs']
        message = f"📗 *Juz' {juz_number}*\n\n"
        current_surah_name = ""
        for ayah in ayahs:
            if ayah['surah']['name'] != current_surah_name:
                current_surah_name = ayah['surah']['name']
                message += f"\n--- {current_surah_name} ---\n"
            message += f"{ayah['numberInSurah']}. {ayah['text']}\n"
        for i in range(0, len(message), 4096):
            send_telegram_message(chat_id, message[i:i+4096])
    except (IndexError, ValueError):
        send_telegram_message(chat_id, MESSAGES[lang]["juz_prompt"])
    except Exception:
        send_telegram_message(chat_id, "Sorry, I could not retrieve the Juz'.")

def handle_recitation(chat_id, args, lang, reciter_key):
    full_audio_url = ""
    try:
        if not args:
            send_telegram_message(chat_id, MESSAGES[lang]["reciter_prompt"].format(reciter_key=reciter_key))
            return
        surah_number = int(args[0])
        if not 1 <= surah_number <= 114: raise ValueError
        
        reciter_info = RECITERS[reciter_key]
        reciter_identifier = reciter_info['identifier']
        
        padded_surah_number = str(surah_number).zfill(3)
        full_audio_url = f"https://download.quranicaudio.com/quran/{reciter_identifier}/{padded_surah_number}.mp3"
        
        surah_info_response = requests.get(f"{QURAN_API_BASE_URL}/surah/{surah_number}")
        surah_name_english = surah_info_response.json()['data']['englishName']
        
        message_text = MESSAGES[lang]["audio_link_message"].format(surah_name_english=surah_name_english, audio_url=full_audio_url)
        send_telegram_message(chat_id, message_text)

    except (IndexError, ValueError):
        send_telegram_message(chat_id, MESSAGES[lang]["reciter_prompt"].format(reciter_key=reciter_key))
    except Exception:
        send_telegram_message(chat_id, MESSAGES[lang]["error_fetching"].format(full_audio_url=full_audio_url))

# --- Admin Commands ---
def handle_status(chat_id):
    db_data = get_db()
    user_count = len(db_data.get('users', [])) if db_data else 'N/A'
    send_telegram_message(chat_id, f"📊 *Bot Status*\n\nTotal Users: *{user_count}*")

def handle_broadcast(admin_id, message_text):
    db_data = get_db()
    if db_data is None:
        send_telegram_message(admin_id, "❌ Could not connect to the database to get user list.")
        return
    
    users = db_data.get('users', [])
    sent_count = 0
    failed_count = 0
    
    for user_id in users:
        try:
            send_telegram_message(user_id, message_text)
            sent_count += 1
            time.sleep(0.1)
        except Exception as e:
            failed_count += 1
            print(f"Could not broadcast to {user_id}: {e}")
    
    send_telegram_message(admin_id, f"✅ Broadcast sent to *{sent_count}* users.\n❌ Failed to send to *{failed_count}* users.")

def handle_debug(chat_id):
    debug_report = "⚙️ *Debug Report*\n\n"
    debug_report += "*Environment Variables:*\n"
    debug_report += f"- ADMIN_ID: {'✅ Set' if ADMIN_ID else '❌ Not Set'}\n"
    debug_report += f"- CHANNEL_ID: {'✅ Set' if CHANNEL_ID else '❌ Not Set'}\n"
    debug_report += f"- JSONBIN_API_KEY: {'✅ Set' if JSONBIN_API_KEY else '❌ Not Set'}\n"
    debug_report += f"- JSONBIN_BIN_ID: {'✅ Set' if JSONBIN_BIN_ID else '❌ Not Set'}\n\n"
    
    debug_report += "*JSONBin.io Connection Test:*\n"
    db_data = get_db()
    if db_data is not None:
        debug_report += f"✅ Connection Successful! Found {len(db_data.get('users', []))} users.\n"
    else:
        debug_report += "❌ Connection Failed! Check API Key, Bin ID, and Bin privacy.\n"
    
    send_telegram_message(chat_id, debug_report)

# --- Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if 'callback_query' in update:
        callback_query = update['callback_query']
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            user_languages[chat_id] = lang_code
            lang = get_user_lang(chat_id)
            send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["language_selected"])
        return 'ok'

    if 'message' in update:
        message = update['message']
        user_id = message['from']['id']
        chat_id = message['chat']['id']
        user_name = message['from'].get('first_name', 'User')
        text = message.get('text', '')
        command_parts = text.split()
        command = command_parts[0].lower() if command_parts else ''
        args = command_parts[1:]
        lang = get_user_lang(chat_id)
        is_admin = str(user_id) == ADMIN_ID
        
        if command == '/start':
            add_user_to_db(user_id)
        
        if not is_admin and not is_user_member(user_id):
            if user_id in member_cache: member_cache.pop(user_id)
            channel_name = CHANNEL_ID.replace('@', '') if CHANNEL_ID else ''
            keyboard = {"inline_keyboard": [[{"text": MESSAGES.get(lang, MESSAGES['en'])["join_button_text"], "url": f"https://t.me/{channel_name}"}]]}
            send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["force_join"], reply_markup=keyboard)
            return 'ok'

        if command == '/start':
            send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["welcome"].format(username=user_name))
        
        elif command == '/language':
            keyboard = {"inline_keyboard": [[{"text": "አማርኛ", "callback_data": "set_lang_am"}, {"text": "English", "callback_data": "set_lang_en"}],[{"text": "العربية", "callback_data": "set_lang_ar"}, {"text": "Türkçe", "callback_data": "set_lang_tr"}]]}
            send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["language_prompt"], reply_markup=keyboard)
        
        elif command == '/support':
            if not args:
                send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["support_prompt"])
            else:
                support_message = " ".join(args)
                forward_message = f"🆘 *New Support Message*\n\n*From:* {user_name} (ID: `{user_id}`)\n\n*Message:* {support_message}"
                if ADMIN_ID: send_telegram_message(ADMIN_ID, forward_message)
                send_telegram_message(chat_id, MESSAGES.get(lang, MESSAGES['en'])["support_sent"])
        
        elif is_admin and command == '/status':
            handle_status(chat_id)
        
        elif is_admin and command == '/broadcast':
            if not args:
                send_telegram_message(chat_id, "Usage: `/broadcast <message>`")
            else:
                broadcast_text = " ".join(args)
                handle_broadcast(chat_id, broadcast_text)
        
        elif is_admin and command == '/debug':
            handle_debug(chat_id)
            
        elif command == '/surah':
            handle_surah(chat_id, args, lang)
        
        elif command == '/juz':
            handle_juz(chat_id, args, lang)
            
        else:
            reciter_command = command.replace('/', '')
            if reciter_command in RECITERS:
                handle_recitation(chat_id, args, lang, reciter_command)

    return 'ok'

@app.route('/')
def index():
    return "Quran Bot is running with all features!"
