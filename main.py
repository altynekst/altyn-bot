import telebot
from telebot import types
import json
import os
import time
from datetime import datetime
from collections import Counter
import hashlib
import requests  # ВАЖНО: добавляем requests

# ================ ТВОИ ДАННЫЕ ================
# 🔥 ТОКЕН УЖЕ ВСТРОЕН! НИЧЕГО ДОБАВЛЯТЬ НЕ НАДО!
BOT_TOKEN = "8147946869:AAF7Xw4XXc0OZUZU3Zir-uhXDEwBDSYMlw8"
ADMIN_ID = 1856968535

# СПИСОК РАЗРЕШЁННЫХ ПОЛЬЗОВАТЕЛЕЙ
ALLOWED_USERS = [
    1856968535, 7969744570, 5338412256, 1884395691, 854516498,
    7757107782, 8362622503, 7041457550, 8169565031, 5544698718
]
# =============================================

# ============== УБИВАЕМ 409 НАВСЕГДА ==============
print("🔄 ЖЁСТКИЙ СБРОС ПОДКЛЮЧЕНИЙ К TELEGRAM...")

# Метод 1: deleteWebhook с drop_pending_updates (100% гарантия)
webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
try:
    response = requests.get(webhook_url, timeout=10)
    print(f"✅ Сброс вебхука: {response.json()}")
except Exception as e:
    print(f"⚠️ Ошибка сброса вебхука: {e}")

# Метод 2: getUpdates с offset=-1 (принудительно завершаем polling)
get_updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&timeout=1"
try:
    requests.get(get_updates_url, timeout=5)
    print("✅ Принудительный сброс polling")
except:
    pass

# Даём Telegram время обработать запросы
time.sleep(2)
print("✅ СБРОС ВЫПОЛНЕН, ЗАПУСКАЕМ БОТА...")
# =============================================

bot = telebot.TeleBot(BOT_TOKEN)

# ФАЙЛЫ ДЛЯ ХРАНЕНИЯ (используем /tmp для Render)
DATA_DIR = '/tmp/bot_data' if os.path.exists('/tmp') else '.'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "answers.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# ============== РАБОТА С ФАЙЛАМИ ==============
def safe_load_json(filename, default):
    try:
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        if os.path.exists(filename):
            try:
                os.rename(filename, f"{filename}.backup_{int(time.time())}")
            except:
                pass
    return default

def safe_save_json(filename, data):
    temp_file = f"{filename}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, filename)
        return True
    except:
        try:
            os.remove(temp_file)
        except:
            pass
        return False

def load_answers():
    return safe_load_json(DATA_FILE, [])

def save_answers(answers):
    return safe_save_json(DATA_FILE, answers)

def load_users():
    return safe_load_json(USERS_FILE, {"allowed": ALLOWED_USERS.copy()})

def save_users(users_data):
    return safe_save_json(USERS_FILE, users_data)

# ============== ДОБАВЛЕНИЕ ОТВЕТА ==============
def add_answer(user_id, subject, file_id, photos_list=None):
    answers = load_answers()
    
    answer_data = {
        "id": len(answers) + 1,
        "user_id": user_id,
        "subject": subject,
        "time": int(time.time()),
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    
    if photos_list:
        answer_data["photos"] = photos_list[:10]
        answer_data["count"] = len(photos_list)
    else:
        answer_data["file_id"] = file_id
        answer_data["count"] = 1
    
    answers.append(answer_data)
    save_answers(answers)
    return answer_data

def delete_answer(answer_id):
    answers = load_answers()
    answers = [a for a in answers if a['id'] != answer_id]
    save_answers(answers)

# ============== КОРОТКИЙ ID ДЛЯ ПРЕДМЕТОВ ==============
SUBJECTS_CACHE = {}

def get_subject_short_id(subject):
    if subject in SUBJECTS_CACHE:
        return SUBJECTS_CACHE[subject]
    short_id = hashlib.md5(subject.encode()).hexdigest()[:10]
    SUBJECTS_CACHE[subject] = short_id
    return short_id

def get_subject_by_short_id(short_id):
    for subject, sid in SUBJECTS_CACHE.items():
        if sid == short_id:
            return subject
    return None

# ============== ПРОВЕРКА ПРАВ ==============
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_allowed(user_id):
    users_data = load_users()
    allowed_users = users_data.get("allowed", ALLOWED_USERS)
    return user_id in allowed_users or is_admin(user_id)

# ============== БЕЗОПАСНАЯ ОТПРАВКА ==============
def safe_send_message(chat_id, text, parse_mode=None, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except:
        return None

def safe_send_photo(chat_id, photo, caption=None, parse_mode=None):
    try:
        return bot.send_photo(chat_id, photo, caption=caption, parse_mode=parse_mode)
    except:
        return None

# ============== КОМАНДА СТАРТ ==============
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        safe_send_message(message.chat.id, "❌ У вас нет доступа к этому боту.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        types.KeyboardButton("📤 ПРИСЛАТЬ ОТВЕТЫ"),
        types.KeyboardButton("📚 ВСЕ ОТВЕТЫ"),
        types.KeyboardButton("🔍 ПОИСК"),
        types.KeyboardButton("📊 СТАТИСТИКА")
    ]
    markup.add(*buttons)
    
    if is_admin(user_id):
        markup.add(types.KeyboardButton("👑 АДМИН ПАНЕЛЬ"))
    
    welcome_text = (
        "👋 *Привет!*\n\n"
        "📥 *Пришли сюда ответы!*\n\n"
        "⚠️ *ВАЖНО!* Обязательно укажи предмет.\n\n"
        "📌 *Примеры:*\n"
        "└ `Всемирная история 8 класс`\n"
        "└ `Алгебра 9 класс`\n\n"
        "👇 *Нажми кнопку ниже*"
    )
    
    safe_send_message(message.chat.id, welcome_text, "Markdown", markup)

# ============== ПРИСЛАТЬ ОТВЕТЫ ==============
@bot.message_handler(func=lambda m: m.text == "📤 ПРИСЛАТЬ ОТВЕТЫ")
def ask_subject(message):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        safe_send_message(message.chat.id, "❌ Нет доступа.")
        return
    
    safe_send_message(
        message.chat.id,
        "📚 *Введи название предмета:*\n\n└ Пример: `Всемирная история`",
        "Markdown"
    )
    bot.register_next_step_handler(message, get_subject)

def get_subject(message):
    user_id = message.from_user.id
    
    if not message.text or message.text.startswith('/'):
        safe_send_message(message.chat.id, "❌ *Ошибка!* Введи название предмета.", "Markdown")
        bot.register_next_step_handler(message, get_subject)
        return
    
    subject = message.text.strip()
    
    if len(subject) > 100:
        safe_send_message(message.chat.id, "❌ *Слишком длинное название!*", "Markdown")
        bot.register_next_step_handler(message, get_subject)
        return
    
    user_data[user_id] = {'subject': subject}
    
    safe_send_message(
        message.chat.id,
        f"✅ *Предмет:* {subject}\n\n📸 *Отправь фото с ответами!*",
        "Markdown"
    )
    bot.register_next_step_handler(message, get_photos)

user_data = {}

def get_photos(message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        safe_send_message(message.chat.id, "❌ Ошибка. Начни заново через /start")
        return
    
    if not message.photo:
        safe_send_message(message.chat.id, "❌ *Отправь фото!*", "Markdown")
        bot.register_next_step_handler(message, get_photos)
        return
    
    subject = user_data[user_id]['subject']
    file_id = message.photo[-1].file_id
    
    try:
        answer_data = add_answer(user_id, subject, file_id)
        
        safe_send_message(
            message.chat.id,
            f"✅ *Готово!*\n\n📚 Предмет: *{subject}*\n🆔 ID: #{answer_data['id']}",
            "Markdown"
        )
        
        # ТОЛЬКО АДМИНУ - информация об отправителе
        username = message.from_user.username or f"ID {user_id}"
        fullname = message.from_user.full_name or "Без имени"
        safe_send_message(
            ADMIN_ID,
            f"📥 *НОВЫЙ ОТВЕТ*\n\n👤 {fullname} (@{username})\n🆔 {user_id}\n📚 {subject}\n🆔 #{answer_data['id']}",
            "Markdown"
        )
        
        del user_data[user_id]
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Ошибка: {str(e)[:100]}")

# ============== ВСЕ ОТВЕТЫ ==============
@bot.message_handler(func=lambda m: m.text == "📚 ВСЕ ОТВЕТЫ")
def show_all_answers(message):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        return
    
    answers = load_answers()
    
    if not answers:
        safe_send_message(message.chat.id, "📭 *Пока нет ответов.*", "Markdown")
        return
    
    subjects = {}
    for ans in answers:
        subjects[ans['subject']] = subjects.get(ans['subject'], 0) + 1
    
    sorted_subjects = sorted(subjects.items(), key=lambda x: x[1], reverse=True)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for subject, count in sorted_subjects[:10]:
        short_id = get_subject_short_id(subject)
        short_name = subject[:15] + "..." if len(subject) > 15 else subject
        markup.add(types.InlineKeyboardButton(
            f"📖 {short_name} ({count})",
            callback_data=f"s_{short_id}"
        ))
    
    if len(subjects) > 10:
        markup.add(types.InlineKeyboardButton("🔍 ВСЕ ПРЕДМЕТЫ", callback_data="all_subjects"))
    
    safe_send_message(
        message.chat.id,
        f"📚 *ВСЕГО ОТВЕТОВ:* {len(answers)}",
        "Markdown",
        markup
    )

# ============== СТАТИСТИКА ==============
@bot.message_handler(func=lambda m: m.text == "📊 СТАТИСТИКА")
def my_stats(message):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        return
    
    answers = load_answers()
    user_answers = [a for a in answers if a['user_id'] == user_id]
    
    if not user_answers:
        safe_send_message(message.chat.id, "📊 *Ты ещё не отправлял ответы*", "Markdown")
        return
    
    subjects = {}
    for ans in user_answers:
        subjects[ans['subject']] = subjects.get(ans['subject'], 0) + 1
    
    best_subject = max(subjects.items(), key=lambda x: x[1]) if subjects else ("Нет", 0)
    total_photos = sum(a.get('count', 1) for a in user_answers)
    
    stats_text = (
        f"📊 *ТВОЯ СТАТИСТИКА*\n\n"
        f"└ Ответов: {len(user_answers)}\n"
        f"└ Фото: {total_photos}\n"
        f"└ Предметов: {len(subjects)}\n"
        f"└ Любимый: {best_subject[0][:20]} ({best_subject[1]})"
    )
    
    safe_send_message(message.chat.id, stats_text, "Markdown")

# ============== ПОИСК ==============
@bot.message_handler(func=lambda m: m.text == "🔍 ПОИСК")
def search_prompt(message):
    user_id = message.from_user.id
    
    if not is_allowed(user_id):
        return
    
    safe_send_message(
        message.chat.id,
        "🔍 *Введи предмет для поиска:*",
        "Markdown"
    )
    bot.register_next_step_handler(message, search_subject)

def search_subject(message):
    query = message.text.strip().lower()
    
    if len(query) < 3:
        safe_send_message(message.chat.id, "❌ *Минимум 3 символа*", "Markdown")
        return
    
    answers = load_answers()
    found = [a for a in answers if query in a['subject'].lower()]
    
    if not found:
        safe_send_message(message.chat.id, f"❌ Ничего не найдено", "Markdown")
        return
    
    subjects = {}
    for ans in found:
        subjects[ans['subject']] = subjects.get(ans['subject'], 0) + 1
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for subject, count in list(subjects.items())[:10]:
        short_id = get_subject_short_id(subject)
        markup.add(types.InlineKeyboardButton(
            f"📖 {subject[:20]} ({count})",
            callback_data=f"s_{short_id}"
        ))
    
    safe_send_message(
        message.chat.id,
        f"🔍 *Найдено:* {len(found)} ответов",
        "Markdown",
        markup
    )

# ============== ПОКАЗ ОТВЕТОВ ==============
@bot.callback_query_handler(func=lambda call: call.data.startswith("s_"))
def show_subject_answers(call):
    user_id = call.from_user.id
    
    if not is_allowed(user_id):
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return
    
    short_id = call.data[2:]
    subject = get_subject_by_short_id(short_id)
    
    if not subject:
        bot.answer_callback_query(call.id, "❌ Не найдено")
        return
    
    answers = load_answers()
    subject_answers = [a for a in answers if a['subject'] == subject]
    
    bot.answer_callback_query(call.id)
    
    safe_send_message(
        call.message.chat.id,
        f"📚 *{subject[:50]}*\n└ Ответов: {len(subject_answers)}",
        "Markdown"
    )
    
    for ans in subject_answers[-5:]:
        caption = f"📚 *{ans['subject'][:30]}*\n🆔 #{ans['id']}\n📅 {ans['date']}"
        
        if is_admin(user_id):
            caption += f"\n🗑 /del_{ans['id']}"
        
        if 'photos' in ans:
            safe_send_photo(call.message.chat.id, ans['photos'][0], caption, "Markdown")
        else:
            safe_send_photo(call.message.chat.id, ans['file_id'], caption, "Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "all_subjects")
def all_subjects(call):
    if not is_allowed(call.from_user.id):
        return
    
    answers = load_answers()
    subjects = {}
    for ans in answers:
        subjects[ans['subject']] = subjects.get(ans['subject'], 0) + 1
    
    text = "📚 *ВСЕ ПРЕДМЕТЫ:*\n\n"
    for subject, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True)[:50]:
        text += f"└ {subject[:50]} — {count}\n"
    
    safe_send_message(call.message.chat.id, text[:4000], "Markdown")
    bot.answer_callback_query(call.id)

# ============== УДАЛЕНИЕ ОТВЕТОВ (ТОЛЬКО АДМИН) ==============
@bot.message_handler(regexp=r'^/del_\d+$')
def delete_answer_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        safe_send_message(message.chat.id, "❌ Только для админа!")
        return
    
    try:
        answer_id = int(message.text.replace('/del_', ''))
        delete_answer(answer_id)
        safe_send_message(message.chat.id, f"✅ Ответ #{answer_id} удалён")
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Ошибка: {str(e)[:50]}")

# ============== АДМИН ПАНЕЛЬ ==============
@bot.message_handler(func=lambda m: m.text == "👑 АДМИН ПАНЕЛЬ")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats"),
        types.InlineKeyboardButton("👥 УПРАВЛЕНИЕ ID", callback_data="admin_users"),
        types.InlineKeyboardButton("➕ ДОБАВИТЬ ID", callback_data="admin_add_user"),
        types.InlineKeyboardButton("❌ УДАЛИТЬ ID", callback_data="admin_remove_user"),
        types.InlineKeyboardButton("📁 БЕКАП БД", callback_data="admin_backup"),
        types.InlineKeyboardButton("🗑 УДАЛИТЬ ОТВЕТ", callback_data="admin_delete_help")
    )
    
    safe_send_message(
        message.chat.id,
        "👑 *АДМИН ПАНЕЛЬ*",
        "Markdown",
        markup
    )

# ============== АДМИН ОБРАБОТЧИК ==============
@bot.callback_query_handler(func=lambda call: call.data.startswith(('admin_', 'remove_id_', 'back_to_admin')))
def admin_callback_handler(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return
    
    if call.data == "admin_stats":
        answers = load_answers()
        users_data = load_users()
        allowed_users = users_data.get("allowed", ALLOWED_USERS)
        
        total_answers = len(answers)
        total_photos = sum(a.get('count', 1) for a in answers)
        total_users = len(set(a['user_id'] for a in answers))
        total_subjects = len(set(a['subject'] for a in answers))
        
        today = datetime.now().strftime("%d.%m.%Y")
        today_answers = [a for a in answers if a['date'].startswith(today)]
        
        stats_text = (
            f"📊 *СТАТИСТИКА*\n\n"
            f"└ Ответов: {total_answers}\n"
            f"└ Фото: {total_photos}\n"
            f"└ Авторов: {total_users}\n"
            f"└ Предметов: {total_subjects}\n"
            f"└ Разрешённых ID: {len(allowed_users)}\n"
            f"└ Сегодня: {len(today_answers)}"
        )
        
        bot.edit_message_text(
            stats_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
            )
        )
    
    elif call.data == "admin_users":
        users_data = load_users()
        allowed_users = users_data.get("allowed", ALLOWED_USERS)
        
        text = "👥 *РАЗРЕШЁННЫЕ ID*\n\n"
        for i, uid in enumerate(allowed_users[:20], 1):
            text += f"{i}. `{uid}`\n"
        
        if len(allowed_users) > 20:
            text += f"... и ещё {len(allowed_users) - 20}"
        
        text += f"\n\n└ Всего: {len(allowed_users)}"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
            )
        )
    
    elif call.data == "admin_add_user":
        bot.edit_message_text(
            "➕ *ДОБАВЛЕНИЕ ID*\n\n📝 Отправьте ID пользователя:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(call.message, admin_add_user_process)
    
    elif call.data == "admin_remove_user":
        users_data = load_users()
        allowed_users = users_data.get("allowed", ALLOWED_USERS)
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for uid in allowed_users[:10]:
            if uid != ADMIN_ID:
                markup.add(types.InlineKeyboardButton(
                    f"❌ {uid}",
                    callback_data=f"remove_id_{uid}"
                ))
        
        markup.add(types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin"))
        
        bot.edit_message_text(
            "❌ *УДАЛЕНИЕ ID*\n\nВыберите ID:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    
    elif call.data.startswith("remove_id_"):
        remove_id = int(call.data.replace("remove_id_", ""))
        
        if remove_id == ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Нельзя удалить админа!", show_alert=True)
            return
        
        users_data = load_users()
        allowed_users = users_data.get("allowed", ALLOWED_USERS)
        
        if remove_id in allowed_users:
            allowed_users.remove(remove_id)
            users_data["allowed"] = allowed_users
            save_users(users_data)
            bot.answer_callback_query(call.id, f"✅ ID {remove_id} удалён!", show_alert=True)
            
            # Обновляем список
            markup = types.InlineKeyboardMarkup(row_width=1)
            for uid in allowed_users[:10]:
                if uid != ADMIN_ID:
                    markup.add(types.InlineKeyboardButton(
                        f"❌ {uid}",
                        callback_data=f"remove_id_{uid}"
                    ))
            markup.add(types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin"))
            
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        else:
            bot.answer_callback_query(call.id, "❌ ID не найден!", show_alert=True)
    
    elif call.data == "admin_backup":
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "rb") as f:
                    bot.send_document(
                        call.message.chat.id,
                        f,
                        caption=f"📁 Бекап • {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                    )
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ {str(e)[:30]}")
        else:
            bot.answer_callback_query(call.id, "❌ Файл не найден!")
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_delete_help":
        bot.edit_message_text(
            "🗑 *УДАЛЕНИЕ ОТВЕТОВ*\n\n"
            "Чтобы удалить ответ, используй:\n"
            "`/del_123`\n\n"
            "Где 123 - ID ответа\n\n"
            "ID виден при просмотре ответа.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ НАЗАД", callback_data="back_to_admin")
            )
        )
    
    elif call.data == "back_to_admin":
        admin_panel(call.message)

def admin_add_user_process(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_user_id = int(message.text.strip())
    except:
        safe_send_message(message.chat.id, "❌ *Ошибка!* Нужно отправить число.", "Markdown")
        return
    
    if new_user_id <= 0:
        safe_send_message(message.chat.id, "❌ *Ошибка!* Некорректный ID.", "Markdown")
        return
    
    users_data = load_users()
    allowed_users = users_data.get("allowed", ALLOWED_USERS)
    
    if new_user_id in allowed_users:
        safe_send_message(message.chat.id, f"❌ ID `{new_user_id}` уже в списке!", "Markdown")
        return
    
    allowed_users.append(new_user_id)
    users_data["allowed"] = allowed_users
    save_users(users_data)
    
    safe_send_message(
        message.chat.id,
        f"✅ *ID добавлен!*\n\n└ `{new_user_id}`\n└ Всего: {len(allowed_users)}",
        "Markdown"
    )

# ============== КОМАНДЫ АДМИНА ==============
@bot.message_handler(commands=['add'])
def admin_add_command(message):
    if not is_admin(message.from_user.id):
        safe_send_message(message.chat.id, "❌ Только для админа.")
        return
    
    try:
        new_id = int(message.text.split()[1])
    except:
        safe_send_message(message.chat.id, "❌ Использование: /add 1234567890")
        return
    
    users_data = load_users()
    allowed_users = users_data.get("allowed", ALLOWED_USERS)
    
    if new_id in allowed_users:
        safe_send_message(message.chat.id, f"❌ ID {new_id} уже в списке.")
        return
    
    allowed_users.append(new_id)
    users_data["allowed"] = allowed_users
    save_users(users_data)
    safe_send_message(message.chat.id, f"✅ ID {new_id} добавлен!")

@bot.message_handler(commands=['del'])
def admin_del_command(message):
    if not is_admin(message.from_user.id):
        safe_send_message(message.chat.id, "❌ Только для админа.")
        return
    
    try:
        del_id = int(message.text.split()[1])
    except:
        safe_send_message(message.chat.id, "❌ Использование: /del 1234567890")
        return
    
    if del_id == ADMIN_ID:
        safe_send_message(message.chat.id, "❌ Нельзя удалить админа!")
        return
    
    users_data = load_users()
    allowed_users = users_data.get("allowed", ALLOWED_USERS)
    
    if del_id in allowed_users:
        allowed_users.remove(del_id)
        users_data["allowed"] = allowed_users
        save_users(users_data)
        safe_send_message(message.chat.id, f"✅ ID {del_id} удалён!")
    else:
        safe_send_message(message.chat.id, f"❌ ID {del_id} не найден.")

# ============== ЗАГЛУШКА ==============
@bot.message_handler(func=lambda m: True)
def fallback(message):
    if is_allowed(message.from_user.id):
        safe_send_message(
            message.chat.id,
            "❓ *Используй кнопки в меню*",
            "Markdown"
        )
    else:
        safe_send_message(message.chat.id, "❌ У вас нет доступа к этому боту.")

# ============== ЗАПУСК ==============
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 БОТ ДЛЯ ОТВЕТОВ ЗАПУЩЕН!")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"📁 Данные: {DATA_FILE}")
    print("=" * 50)
    print("✅ Токен ВСТРОЕН в код")
    print("✅ 409 УБИТА - сброс вебхука ДО запуска")
    print("=" * 50)
    
    # Бесконечный перезапуск с защитой от 409
    while True:
        try:
            # Перед каждым перезапуском сбрасываем вебхук
            try:
                requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
                time.sleep(1)
            except:
                pass
            
            bot.polling(non_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
            continue