import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from collections import Counter
import hashlib
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================ ТВОИ ДАННЫЕ ================
BOT_TOKEN = "8147946869:AAF7Xw4XXc0OZUZU3Zir-uhXDEwBDSYMlw8"
ADMIN_ID = 1856968535

ALLOWED_USERS = [
    1856968535, 7969744570, 5338412256, 1884395691, 854516498,
    7757107782, 8362622503, 7041457550, 8169565031, 5544698718
]
# =============================================

# ============== HEALTH CHECK ==============
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, format, *args): pass

def run_health_server():
    port = 10000
    while True:
        try:
            server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            print(f"✅ HEALTH CHECK НА ПОРТУ {port}")
            server.serve_forever()
        except:
            time.sleep(3)
            continue

threading.Thread(target=run_health_server, daemon=True).start()
# =============================================

# ============== СБРОС 409 ==============
print("🔄 СБРОС WEBHOOK")
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
time.sleep(2)
# =============================================

bot = telebot.TeleBot(BOT_TOKEN)

# ============== ФАЙЛЫ ==============
DATA_DIR = '/tmp/bot_data' if os.path.exists('/tmp') else '.'
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "answers.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def load_answers():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_answers(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"allowed": ALLOWED_USERS.copy()}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
# ======================================

user_data = {}
SUBJECTS_CACHE = {}

def get_subject_short_id(subject):
    if subject not in SUBJECTS_CACHE:
        SUBJECTS_CACHE[subject] = hashlib.md5(subject.encode()).hexdigest()[:10]
    return SUBJECTS_CACHE[subject]

def get_subject_by_short_id(short_id):
    for s, sid in SUBJECTS_CACHE.items():
        if sid == short_id:
            return s
    return None

def is_admin(uid): return uid == ADMIN_ID
def is_allowed(uid):
    d = load_users()
    return uid in d.get("allowed", ALLOWED_USERS) or is_admin(uid)

# ============== ОТПРАВКА ФОТО (ЖЁСТКО) ==============
def send_photo_force(chat_id, file_id, caption):
    try:
        bot.send_photo(chat_id, file_id, caption=caption, parse_mode="Markdown")
        return True
    except Exception as e:
        print(f"❌ Ошибка фото: {e}")
        try:
            bot.send_message(chat_id, f"⚠️ Фото не загрузилось\n{caption}")
        except:
            pass
        return False
# ===================================================

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if not is_allowed(uid):
        bot.send_message(message.chat.id, "❌ Нет доступа.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📤 ПРИСЛАТЬ ОТВЕТЫ"),
        types.KeyboardButton("📚 ВСЕ ОТВЕТЫ"),
        types.KeyboardButton("📊 СТАТИСТИКА")
    )
    if is_admin(uid):
        markup.add(types.KeyboardButton("👑 АДМИН ПАНЕЛЬ"))

    bot.send_message(
        message.chat.id,
        "👋 *Привет!*\n📥 *Пришли ответы с фото и предметом*",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ============== ПРИСЛАТЬ ОТВЕТЫ ==============
@bot.message_handler(func=lambda m: m.text == "📤 ПРИСЛАТЬ ОТВЕТЫ")
def ask_subject(m):
    if not is_allowed(m.from_user.id):
        return
    bot.send_message(m.chat.id, "📚 *Введи название предмета:*", parse_mode="Markdown")
    bot.register_next_step_handler(m, get_subject)

def get_subject(m):
    uid = m.from_user.id
    if not m.text or m.text.startswith('/'):
        bot.send_message(m.chat.id, "❌ Название предмета.")
        return
    subject = m.text.strip()[:100]
    user_data[uid] = {'subject': subject}
    bot.send_message(m.chat.id, f"✅ *{subject}*\n📸 Отправь фото", parse_mode="Markdown")
    bot.register_next_step_handler(m, get_photos)

def get_photos(m):
    uid = m.from_user.id
    if uid not in user_data:
        bot.send_message(m.chat.id, "❌ Начни заново /start")
        return
    if not m.photo:
        bot.send_message(m.chat.id, "❌ Отправь фото")
        bot.register_next_step_handler(m, get_photos)
        return

    subject = user_data[uid]['subject']
    file_id = m.photo[-1].file_id

    answers = load_answers()
    aid = len(answers) + 1
    answers.append({
        "id": aid,
        "user_id": uid,
        "subject": subject,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "file_id": file_id
    })
    save_answers(answers)
    bot.send_message(m.chat.id, f"✅ Готово! ID #{aid}")
    bot.send_message(ADMIN_ID, f"📥 Новый ответ\nID #{aid}\nПредмет: {subject}")
    del user_data[uid]

# ============== ВСЕ ОТВЕТЫ ==============
@bot.message_handler(func=lambda m: m.text == "📚 ВСЕ ОТВЕТЫ")
def show_all_answers(m):
    if not is_allowed(m.from_user.id):
        return
    answers = load_answers()
    if not answers:
        bot.send_message(m.chat.id, "📭 Пусто")
        return

    subs = {}
    for a in answers:
        subs[a['subject']] = subs.get(a['subject'], 0) + 1

    markup = types.InlineKeyboardMarkup(row_width=1)
    for sub, cnt in sorted(subs.items(), key=lambda x: x[1], reverse=True)[:10]:
        short = sub[:15] + '...' if len(sub) > 15 else sub
        markup.add(types.InlineKeyboardButton(
            f"📖 {short} ({cnt})",
            callback_data=f"s_{get_subject_short_id(sub)}"
        ))
    if len(subs) > 10:
        markup.add(types.InlineKeyboardButton("📚 ВСЕ ПРЕДМЕТЫ", callback_data="all_subjects"))
    bot.send_message(m.chat.id, f"📚 Всего ответов: {len(answers)}", reply_markup=markup)

# ============== ПОКАЗ ФОТО ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("s_"))
def show_answers(call):
    uid = call.from_user.id
    if not is_allowed(uid):
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    subject = get_subject_by_short_id(call.data[2:])
    if not subject:
        bot.answer_callback_query(call.id, "❌ Не найдено")
        return

    answers = [a for a in load_answers() if a['subject'] == subject]
    bot.answer_callback_query(call.id)

    if not answers:
        bot.send_message(call.message.chat.id, "❌ Нет ответов")
        return

    bot.send_message(call.message.chat.id, f"📚 *{subject[:50]}*\n└ Ответов: {len(answers)}", parse_mode="Markdown")

    for a in answers[-5:]:
        caption = f"📚 *{a['subject'][:30]}*\n🆔 #{a['id']}\n📅 {a['date']}"
        if is_admin(uid):
            caption += f"\n🗑 /del_{a['id']}"
        send_photo_force(call.message.chat.id, a['file_id'], caption)

@bot.callback_query_handler(func=lambda c: c.data == "all_subjects")
def all_subjects(call):
    if not is_allowed(call.from_user.id):
        return
    subs = {}
    for a in load_answers():
        subs[a['subject']] = subs.get(a['subject'], 0) + 1
    text = "📚 *ВСЕ ПРЕДМЕТЫ*\n\n"
    for s, c in sorted(subs.items(), key=lambda x: x[1], reverse=True)[:50]:
        text += f"└ {s[:50]} — {c}\n"
    bot.send_message(call.message.chat.id, text[:4000], parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# ============== СТАТИСТИКА ==============
@bot.message_handler(func=lambda m: m.text == "📊 СТАТИСТИКА")
def stats(m):
    uid = m.from_user.id
    if not is_allowed(uid):
        return
    ua = [a for a in load_answers() if a['user_id'] == uid]
    if not ua:
        bot.send_message(m.chat.id, "📊 Ты ещё не отправлял ответы")
        return
    subs = {}
    for a in ua:
        subs[a['subject']] = subs.get(a['subject'], 0) + 1
    best = max(subs.items(), key=lambda x: x[1]) if subs else ("—", 0)
    bot.send_message(m.chat.id,
        f"📊 *ТВОЯ СТАТИСТИКА*\n\n"
        f"└ Ответов: {len(ua)}\n"
        f"└ Предметов: {len(subs)}\n"
        f"└ Любимый: {best[0][:20]} ({best[1]})",
        parse_mode="Markdown"
    )

# ============== УДАЛЕНИЕ ==============
@bot.message_handler(regexp=r'^/del_\d+$')
def delete_answer(m):
    if not is_admin(m.from_user.id):
        bot.send_message(m.chat.id, "❌ Только админ")
        return
    try:
        aid = int(m.text.replace('/del_', ''))
        answers = [a for a in load_answers() if a['id'] != aid]
        save_answers(answers)
        bot.send_message(m.chat.id, f"✅ #{aid} удалён")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

# ============== АДМИН ПАНЕЛЬ ==============
@bot.message_handler(func=lambda m: m.text == "👑 АДМИН ПАНЕЛЬ")
def admin_panel(m):
    if not is_admin(m.from_user.id):
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats"),
        types.InlineKeyboardButton("👥 УПРАВЛЕНИЕ ID", callback_data="admin_users"),
        types.InlineKeyboardButton("➕ ДОБАВИТЬ ID", callback_data="admin_add_user"),
        types.InlineKeyboardButton("❌ УДАЛИТЬ ID", callback_data="admin_remove_user"),
        types.InlineKeyboardButton("📁 БЕКАП", callback_data="admin_backup")
    )
    bot.send_message(m.chat.id, "👑 *АДМИН ПАНЕЛЬ*", parse_mode="Markdown", reply_markup=markup)

# ============== АДМИН ЛОГИКА ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith(('admin_', 'remove_id_', 'back_to_admin')))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return
    data = call.data

    if data == "admin_stats":
        a = load_answers()
        u = load_users()
        bot.edit_message_text(
            f"📊 *СТАТИСТИКА*\n\n└ Ответов: {len(a)}\n└ Авторов: {len(set(x['user_id'] for x in a))}\n└ Предметов: {len(set(x['subject'] for x in a))}\n└ Разрешённых ID: {len(u.get('allowed', []))}",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin"))
        )
    elif data == "admin_users":
        u = load_users()
        text = "👥 *РАЗРЕШЁННЫЕ ID*\n\n" + "\n".join(f"{i+1}. `{uid}`" for i, uid in enumerate(u.get("allowed", [])[:20]))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")))
    elif data == "admin_add_user":
        bot.edit_message_text("➕ *ДОБАВИТЬ ID*\nОтправь ID:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, admin_add_user_process)
    elif data == "admin_remove_user":
        u = load_users()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for uid in u.get("allowed", [])[:10]:
            if uid != ADMIN_ID:
                markup.add(types.InlineKeyboardButton(f"❌ {uid}", callback_data=f"remove_id_{uid}"))
        markup.add(types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin"))
        bot.edit_message_text("❌ *УДАЛИТЬ ID*", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    elif data.startswith("remove_id_"):
        rid = int(data.replace("remove_id_", ""))
        if rid == ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Нельзя удалить админа", show_alert=True)
            return
        u = load_users()
        if rid in u["allowed"]:
            u["allowed"].remove(rid)
            save_users(u)
            bot.answer_callback_query(call.id, f"✅ {rid} удалён", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Не найден", show_alert=True)
    elif data == "admin_backup":
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                bot.send_document(call.message.chat.id, f, caption=f"📁 Бекап {datetime.now().strftime('%d.%m.%Y')}")
        bot.answer_callback_query(call.id)
    elif data == "back_to_admin":
        admin_panel(call.message)

def admin_add_user_process(m):
    if not is_admin(m.from_user.id):
        return
    try:
        new_id = int(m.text.strip())
        u = load_users()
        if new_id not in u["allowed"]:
            u["allowed"].append(new_id)
            save_users(u)
            bot.send_message(m.chat.id, f"✅ ID {new_id} добавлен")
        else:
            bot.send_message(m.chat.id, "❌ Уже есть")
    except:
        bot.send_message(m.chat.id, "❌ Ошибка")

# ============== ЗАПУСК ==============
if __name__ == "__main__":
    print("🚀 БОТ ЗАПУЩЕН")
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ {e}, рестарт...")
            time.sleep(5)