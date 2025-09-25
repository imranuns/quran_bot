# -*- coding: utf-8 -*-

"""
Al-Quran Kerym Bot - Telegram Bot (Python Version)
Developed for Vercel Serverless Deployment using Flask.

ይህ ፋይል የቴሌግራም ቦቱን ዋና ሎጂክ በፓይተን ቋንቋ ይይዛል።
ተጠቃሚው የተለያዩ ትዕዛዞችን ሲልክ፣ ቦቱ ከቁርአን API መረጃ በመውሰድ ምላሽ ይሰጣል።
"""

import os
import telebot
import requests
from flask import Flask, request

# --- የማዋቀሪያ ተለዋዋጮች (Configurations) ---
try:
    # የቴሌግራም ቶክንን እና የአድሚን ስምን ከ Vercel Environment Variables መውሰድ
    TOKEN = os.environ['TELEGRAM_TOKEN']
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'የአድሚኑን_ስም_ያለ_@_እዚህ_ያስገቡ')
except KeyError:
    # ይህ ኮድ በኮምፒውተርዎ ላይ ሲሞክሩት እንዲሰራ ነው
    # ከ Vercel ውጪ ሲሆን .env ፋይል መጠቀም ይችላሉ (ለደህንነት ሲባል)
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.environ['TELEGRAM_TOKEN']
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'የአድሚኑን_ስም_ያለ_@_እዚህ_ያስገቡ')


# የቁርአን ኦዲዮ እና ጽሁፍ API አድራሻዎች
AUDIO_BASE_URL = {
    'abdulbasit': 'https://server11.mp3quran.net/basit',  # Abdul Basit (Murattal)
    'yasser': 'https://server11.mp3quran.net/yasser',    # Yasser Al-Dosari
}
TEXT_API_BASE_URL = 'https://api.alquran.cloud/v1'

# --- የቦት እና የድር መተግበሪያ ማስጀመሪያ ---
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__) # ለ Vercel የሚያስፈልግ የድር መተግበሪያ

# --- ረዳት ፋንክሽኖች ---
def pad_to_three(num):
    """ቁጥርን ወደ ሶስት አሃዝ (ለምሳሌ 1 -> "001") የሚቀይር ፋንክሽን"""
    return str(num).zfill(3)

# --- የቦት ትዕዛዝ አንቀሳቃሾች (Command Handlers) ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """ለ /start እና /help ትዕዛዞች ምላሽ የሚሰጥ"""
    help_text = """
🕌 *አዲሱ የቁርአን ከሪም ቦት!* 🕌
السلام عليكم ورحمة الله وبركاته

ቁርአንን በቀላሉ ለማንበብ እና ለማዳመጥ የሚያስችል ቦት ነው።

📖 *በጽሁፍ ለማንበብ:*
• `/surah <የሱራ ቁጥር>` - ሙሉ ሱራ ለማግኘት (ምሳሌ: `/surah 1`)
• `/juz <የጁዝ ቁጥር>` - ሙሉ ጁዝ ለማግኘት (ምሳሌ: `/juz 30`)

🔊 *በድምጽ ለማዳመጥ:*
• `/abdulbasit <የሱራ ቁጥር>` 🎙️ (ምሳሌ: `/abdulbasit 1`)
• `/yasser <የሱራ ቁጥር>` 🎧 (ምሳሌ: `/yasser 1`)

⚙️ *ሌሎች ትዕዛዞች:*
• `/language` - ቋንቋ ለመቀየር
• `/support` - ለአስተዳዳሪው መልዕክት ለመላክ
• `/help` - ይህንን መረጃ እንደገና ለማየት

👇 *ቦቱን ለወዳጆችዎ ያጋሩ!*
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['surah'])
def get_surah(message):
    """የተጠየቀውን ሱራ በጽሁፍ የሚልክ"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, 'እባክዎ የሱራውን ቁጥር ያስገቡ። ምሳሌ: /surah 1')
            return
        
        surah_number = int(parts[1])
        if not 1 <= surah_number <= 114:
            bot.reply_to(message, 'እባክዎ ትክክለኛ የሱራ ቁጥር ከ 1 እስከ 114 ያስገቡ።')
            return

        bot.reply_to(message, f"📖 ሱራ ቁጥር {surah_number} በመጫን ላይ ነው... እባክዎ ትንሽ ይጠብቁ።")
        
        response = requests.get(f"{TEXT_API_BASE_URL}/surah/{surah_number}")
        response.raise_for_status() # ስህተት ካለ እዚሁ ያቆማል
        
        data = response.json()['data']
        surah_text = f"*{data['name']} ({data['englishName']})*\n\n"
        
        for ayah in data['ayahs']:
            surah_text += f"{ayah['text']} ({ayah['numberInSurah']}) "
            
        # የቴሌግራም መልዕክት ገደብ (4096) እንዳያልፍ መቆጣጠር
        if len(surah_text) > 4096:
            for i in range(0, len(surah_text), 4096):
                bot.send_message(message.chat.id, surah_text[i:i+4096], parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, surah_text, parse_mode='Markdown')

    except (ValueError, IndexError):
        bot.reply_to(message, 'ትክክል ያልሆነ አገባብ ነው። ምሳሌ: /surah 1')
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"ስህተት አጋጥሟል: ሱራውን ማግኘት አልተቻለም። እባክዎ ቆይተው ይሞክሩ።\nError: {e}")

@bot.message_handler(commands=['juz'])
def get_juz(message):
    """የተጠየቀውን ጁዝ በጽሁፍ የሚልክ"""
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, 'እባክዎ የጁዙን ቁጥር ያስገቡ። ምሳሌ: /juz 1')
            return
            
        juz_number = int(parts[1])
        if not 1 <= juz_number <= 30:
            bot.reply_to(message, 'እባክዎ ትክክለኛ የጁዝ ቁጥር ከ 1 እስከ 30 ያስገቡ።')
            return
        
        bot.reply_to(message, f"📖 ጁዝ ቁጥር {juz_number} በመጫን ላይ ነው...")
        
        response = requests.get(f"{TEXT_API_BASE_URL}/juz/{juz_number}")
        response.raise_for_status()
        
        data = response.json()['data']
        juz_text = f"*ጁዝ {juz_number}*\n"
        current_surah = ""
        
        for ayah in data['ayahs']:
            surah_name = ayah['surah']['name']
            if surah_name != current_surah:
                juz_text += f"\n\n-- *{surah_name}* --\n\n"
                current_surah = surah_name
            juz_text += f"{ayah['text']} ({ayah['numberInSurah']}) "

        if len(juz_text) > 4096:
            for i in range(0, len(juz_text), 4096):
                bot.send_message(message.chat.id, juz_text[i:i+4096], parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, juz_text, parse_mode='Markdown')
            
    except (ValueError, IndexError):
        bot.reply_to(message, 'ትክክል ያልሆነ አገባብ ነው። ምሳሌ: /juz 1')
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"ስህተት አጋጥሟል: ጁዙን ማግኘት አልተቻለም።\nError: {e}")

@bot.message_handler(commands=['abdulbasit', 'yasser'])
def get_audio(message):
    """የተጠየቀውን ሱራ በድምጽ የሚልክ"""
    try:
        command = message.text.split()[0][1:] # '/abdulbasit' -> 'abdulbasit'
        reciter_name = "Abdul Basit" if command == "abdulbasit" else "Yasser Al-Dosari"

        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, f'እባክዎ የሱራውን ቁጥር ያስገቡ። ምሳሌ: /{command} 1')
            return
            
        surah_number = int(parts[1])
        if not 1 <= surah_number <= 114:
            bot.reply_to(message, 'እባክዎ ትክክለኛ የሱራ ቁጥር ከ 1 እስከ 114 ያስገቡ።')
            return

        bot.reply_to(message, f"🔊 ሱራ ቁጥር {surah_number} በቃሪዕ {reciter_name} በመጫን ላይ ነው... እባክዎ ትንሽ ይጠብቁ።")
        
        audio_url = f"{AUDIO_BASE_URL[command]}/{pad_to_three(surah_number)}.mp3"
        
        # የሱራውን ስም ለማምጣት
        surah_info_res = requests.get(f"{TEXT_API_BASE_URL}/surah/{surah_number}")
        surah_info_res.raise_for_status()
        surah_name = surah_info_res.json()['data']['name']
        
        caption = f"📖 ሱራ: {surah_name}\n🎙️ ቃሪዕ: {reciter_name}"
        
        bot.send_audio(message.chat.id, audio_url, caption=caption, timeout=50)

    except (ValueError, IndexError):
        bot.reply_to(message, f'ትክክል ያልሆነ አገባብ ነው። ምሳሌ: /{message.text.split()[0][1:]} 1')
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"ስህተት አጋጥሟል: ኦዲዮውን መላክ አልተቻለም።\nError: {e}")

@bot.message_handler(commands=['language'])
def set_language(message):
    """የቋንቋ መረጃ የሚሰጥ"""
    bot.reply_to(message, '🌐 በአሁኑ ሰዓት ቦቱ በአማርኛ እና በእንግሊዝኛ ትዕዛዞችን ይቀበላል።')

@bot.message_handler(commands=['support'])
def send_support(message):
    """የአድሚኑን አድራሻ የሚልክ"""
    bot.reply_to(message, f"💬 ለአስተያየትና ድጋፍ የአስተዳዳሪውን አካውንት @{ADMIN_USERNAME} ላይ ማግኘት ይችላሉ።")


# --- Vercel Webhook Handler ---
# ይህ ክፍል Vercel ከቴሌግራም ጋር እንዲገናኝ ያደርገዋል
@app.route(f"/", methods=['POST'])
def webhook():
    """ቴሌግራም ጥያቄ ሲልክ የሚቀበል"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Bad Request', 400

# ይህንን መጨመር Vercel እንዲያውቀው ይረዳል
# Vercel ላይ ሲሆን 'app'ን በራስ-ሰር ያገኘዋል።
# በኮምፒውተርዎ ላይ ለመሞከር ከፈለጉ የFlask ሰርቨሩን ማስጀመር ይችላሉ
if __name__ == "__main__":
    # የዌብሁክን መረጃ ማግኘት (አማራጭ)
    bot.remove_webhook()
    # bot.set_webhook(url='የእርስዎ ngrok/repl.it ዩአርኤል እዚህ')
    # app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    pass # Vercel ላይ ሲሆን ይህ ክፍል አይሰራም
