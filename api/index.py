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
        "surah_prompt": "እባክዎ ከቃሪኡ ስም ቀጥሎ የሱራውን ቁጥር ያስገቡ (1-114)።\nአጠቃቀም: `/{reciter_key} 2`",
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
        "surah_prompt": "Please provide the Surah number after the reciter's name (1-114).\nUsage: `/{reciter_key} 2`",
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
        "surah_prompt": "يرجى تقديم رقم السورة بعد اسم القارئ (1-114).\nاستخدام: `/{reciter_key} 2`",
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
        "surah_prompt": "Lütfen okuyucunun adından sonra Sure numarasını girin (1-114).\nKullanım: `/{reciter_key} 2`",
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

def handle_surah(chat_id, args, lang):
    # Implementation... (omitted for brevity, same as before)
    pass

def handle_juz(chat_id, args, lang):
    # Implementation... (omitted for brevity, same as before)
    pass

def handle_recitation(chat_id, args, lang, reciter_key):
    # Implementation... (omitted for brevity, same as before)
    pass

# --- Admin Commands ---
def handle_status(chat_id):
    # Implementation... (omitted for brevity, same as before)
    pass

def handle_broadcast(admin_id, message_text):
    # Implementation... (omitted for brevity, same as before)
    pass

def handle_debug(chat_id):
    # Implementation... (omitted for brevity, same as before)
    pass

# --- Webhook Handler ---
@app.route('/', methods=['POST'])
def webhook():
    update = request.get_json()

    # Handle Callbacks (Buttons)
    if 'callback_query' in update:
        callback_query = update['callback_query']
        data = callback_query['data']
        chat_id = callback_query['message']['chat']['id']
        if data.startswith('set_lang_'):
            lang_code = data.split('_')[-1]
            user_languages[chat_id] = lang_code
            lang = get_user_lang(chat_id)
            send_telegram_message(chat_id, MESSAGES[lang]["language_selected"])
        return 'ok'

    # Handle Messages
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

        # Add user to DB on first interaction
        if command == '/start':
            add_user_to_db(user_id)

        # Force Join Check
        if not is_admin and not is_user_member(user_id):
            if user_id in member_cache: member_cache.pop(user_id) # Clear cache if not a member
            channel_name = CHANNEL_ID.replace('@', '') if CHANNEL_ID else ''
            keyboard = {"inline_keyboard": [[{"text": MESSAGES[lang]["join_button_text"], "url": f"https://t.me/{channel_name}"}]]}
            send_telegram_message(chat_id, MESSAGES[lang]["force_join"], reply_markup=keyboard)
            return 'ok'

        # Command Handling
        if command == '/start':
            send_telegram_message(chat_id, MESSAGES[lang]["welcome"].format(username=user_name))

        elif command == '/language':
            keyboard = {"inline_keyboard": [[{"text": "አማርኛ", "callback_data": "set_lang_am"}, {"text": "English", "callback_data": "set_lang_en"}],[{"text": "العربية", "callback_data": "set_lang_ar"}, {"text": "Türkçe", "callback_data": "set_lang_tr"}]]}
            send_telegram_message(chat_id, MESSAGES[lang]["language_prompt"], reply_markup=keyboard)

        # Other commands... (surah, juz, support, status, etc. - omitted for brevity)

    return 'ok'

@app.route('/')
def index():
    return "Quran Bot is running with all features!"
