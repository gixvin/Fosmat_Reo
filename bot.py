import telebot
from telebot import types
import json
import datetime
import os

BOT_TOKEN = '7059297292:AAEJxAeGBJWISqUj_kjJWAqt1ePh-JpNGTA'
ADMINS = [7805656632, 6307467830]
ADMIN_CHAT_ID = -1002819687378

bot = telebot.TeleBot(BOT_TOKEN)

works_bot = True  # True - бот работает, False - техработы
user_orders = {}
blocked_users = set()

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False)

all_users = load_users()

services = {
    "account_delete": ("Снести аккаунт", "100 грн"),
    "deanon": ("Деанон", "70 грн"),
    "fraud": ("Валид", "90 грн"),
    "channel_delete": ("Снести канал", "120 грн"),
    "email_delete": ("Снести email почти", "90 грн"),
    "card_block": ("Заблокировать банковскую карту", "230 грн")
}


@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    if cid in blocked_users:
        bot.send_message(cid, "⛔ Вы заблокированы.")
        return

    all_users.add(cid)
    save_users(all_users)

    kb = types.InlineKeyboardMarkup()

    if works_bot:
        kb.add(types.InlineKeyboardButton("📦 Сделать заказ", callback_data="order"))
    else:
        kb.add(types.InlineKeyboardButton("⚠️ Бот на техработах", callback_data="disabled"))

    kb.add(
        types.InlineKeyboardButton("📝 Отзывы", url="https://t.me/BetaForm_01"),
        types.InlineKeyboardButton("📢 Канал", url="https://t.me/BetaForm_01"),
        types.InlineKeyboardButton("👨‍💻 Разработчик", url="https://t.me/klas03")
    )

    if cid in ADMINS:
        status_text = "ВЫКЛ" if not works_bot else "ВКЛ"
        kb.add(types.InlineKeyboardButton(f"🔐 Админ меню (бот {status_text})", callback_data="admin_menu"))

    bot.send_message(cid, "Привет! Выбери пункт меню:", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    global works_bot
    cid = call.message.chat.id

    if call.data == "order":
        if not works_bot and cid not in ADMINS:
            bot.answer_callback_query(call.id, "Бот сейчас на технических работах.", show_alert=True)
            return

        kb = types.InlineKeyboardMarkup()
        for key, (name, price) in services.items():
            kb.add(types.InlineKeyboardButton(f"{name} – {price}", callback_data=f"service_{key}"))
        kb.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
        bot.edit_message_text("Выберите услугу:", cid, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("service_"):
        if not works_bot and cid not in ADMINS:
            bot.answer_callback_query(call.id, "Бот сейчас на технических работах.", show_alert=True)
            return

        service_key = call.data[len("service_"):]
        if service_key not in services:
            bot.answer_callback_query(call.id, "Ошибка: сервис не найден", show_alert=True)
            return

        service_name = services[service_key][0]
        user_orders[cid] = service_name
        bot.edit_message_text(f"✅ Заказ '{service_name}' принят и передан администрации. С вами свяжутся.", cid, call.message.message_id)
        notify_admins(call.from_user, service_key)
        log_order(call.from_user, service_name)

    elif call.data == "back":
        start(call.message)

    elif call.data == "admin_menu" and cid in ADMINS:
        status_text = "ВЫКЛ" if not works_bot else "ВКЛ"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📥 Заказы", callback_data="view_orders"),
            types.InlineKeyboardButton("➕ Выдать админа", callback_data="add_admin"),
            types.InlineKeyboardButton("❌ Удалить админа", callback_data="remove_admin"),
            types.InlineKeyboardButton("🔒 Заблокировать пользователя", callback_data="block_user"),
            types.InlineKeyboardButton("🔓 Разблокировать пользователя", callback_data="unblock_user"),
            types.InlineKeyboardButton(f"⚙️ Бот {status_text}", callback_data="toggle_bot")
        )
        bot.edit_message_text("🔐 Админ меню:", cid, call.message.message_id, reply_markup=kb)

    elif call.data == "toggle_bot" and cid in ADMINS:
        works_bot = not works_bot

        if not works_bot:
            for uid in all_users:
                try:
                    bot.send_message(uid, "⚠️ Бот ушёл на технические работы. Скоро вернёмся!")
                except Exception as e:
                    print(f"❌ Не удалось отправить сообщение {uid}: {e}")
        else:
            for uid in all_users:
                try:
                    bot.send_message(uid, "✅ Бот снова работает! Заходи и заказывай.")
                except Exception as e:
                    print(f"❌ Не удалось отправить сообщение {uid}: {e}")

        status = "включен" if works_bot else "выключен"
        bot.answer_callback_query(call.id, f"Бот теперь {status}.")

        status_text = "ВЫКЛ" if not works_bot else "ВКЛ"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📥 Заказы", callback_data="view_orders"),
            types.InlineKeyboardButton("➕ Выдать админа", callback_data="add_admin"),
            types.InlineKeyboardButton("❌ Удалить админа", callback_data="remove_admin"),
            types.InlineKeyboardButton("🔒 Заблокировать пользователя", callback_data="block_user"),
            types.InlineKeyboardButton("🔓 Разблокировать пользователя", callback_data="unblock_user"),
            types.InlineKeyboardButton(f"⚙️ Бот {status_text}", callback_data="toggle_bot")
        )
        bot.edit_message_reply_markup(cid, call.message.message_id, reply_markup=kb)

    elif call.data == "view_orders":
        text = "🗂 Последние заказы:\n"
        for uid, service in user_orders.items():
            text += f"👤 {uid} — {service}\n"
        bot.send_message(cid, text if user_orders else "Нет заказов.")

    elif call.data == "add_admin":
        bot.send_message(cid, "Введите ID пользователя, которого нужно сделать админом:")
        bot.register_next_step_handler(call.message, process_add_admin)

    elif call.data == "remove_admin":
        bot.send_message(cid, "Введите ID админа, которого нужно удалить:")
        bot.register_next_step_handler(call.message, process_remove_admin)

    elif call.data == "block_user":
        bot.send_message(cid, "Введите ID пользователя для блокировки:")
        bot.register_next_step_handler(call.message, process_block_user)

    elif call.data == "unblock_user":
        bot.send_message(cid, "Введите ID пользователя для разблокировки:")
        bot.register_next_step_handler(call.message, process_unblock_user)

    elif call.data.startswith("take_"):
        parts = call.data.split("_")
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "Некорректные данные.", show_alert=True)
            return
        uid = int(parts[1])
        service_key = parts[2]
        service_name = services.get(service_key, ("Неизвестная услуга",))[0]
        if call.from_user.id in ADMINS:
            try:
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                for admin_id in ADMINS:
                    if admin_id != call.from_user.id:
                        bot.send_message(admin_id, f"ℹ️ Заказ от {uid} ({service_name}) уже в работе у @{call.from_user.username or call.from_user.id}.")
                bot.send_message(call.message.chat.id, f"✅ Заказ взят в работу админом @{call.from_user.username or call.from_user.id}.")
                bot.send_message(uid, f"👨‍💼 Ваш заказ '{service_name}' принят в работу администратором. Он скоро с вами свяжется.")
            except Exception as e:
                print("Ошибка при взятии заказа в работу:", e)


@bot.callback_query_handler(func=lambda call: call.data == "disabled")
def disabled_notice(call):
    bot.answer_callback_query(call.id, "Бот сейчас на технических работах. Заказы временно недоступны.", show_alert=True)


def process_add_admin(message):
    try:
        new_id = int(message.text)
        if new_id not in ADMINS:
            ADMINS.append(new_id)
            bot.send_message(message.chat.id, f"✅ {new_id} добавлен в админы.")
        else:
            bot.send_message(message.chat.id, f"⚠️ {new_id} уже админ.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")


def process_remove_admin(message):
    try:
        rem_id = int(message.text)
        if rem_id in ADMINS:
            ADMINS.remove(rem_id)
            bot.send_message(message.chat.id, f"❌ {rem_id} удален из админов.")
        else:
            bot.send_message(message.chat.id, f"⚠️ {rem_id} не найден среди админов.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")


def process_block_user(message):
    try:
        uid = int(message.text)
        blocked_users.add(uid)
        bot.send_message(message.chat.id, f"🔒 Пользователь {uid} заблокирован.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")


def process_unblock_user(message):
    try:
        uid = int(message.text)
        blocked_users.discard(uid)
        bot.send_message(message.chat.id, f"🔓 Пользователь {uid} разблокирован.")
    except:
        bot.send_message(message.chat.id, "❌ Неверный ID.")


def notify_admins(user, service_key):
    service_name = services.get(service_key, ("Неизвестная услуга",))[0]
    text = f"📥 Новый заказ\n👤 Пользователь: @{user.username or user.first_name}\n🛠 Услуга: {service_name}\n🕒 Время: сейчас"
    order_btn = types.InlineKeyboardMarkup()
    order_btn.add(types.InlineKeyboardButton("✅ Взять в работу", callback_data=f"take_{user.id}_{service_key}"))
    for admin_id in ADMINS:
        bot.send_message(admin_id, text)
    bot.send_message(ADMIN_CHAT_ID, text, reply_markup=order_btn)


def log_order(user, service_name):
    order = {
        "user_id": user.id,
        "username": user.username,
        "service": service_name,
        "timestamp": datetime.datetime.now().isoformat()
    }
    try:
        with open("orders_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(order, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Ошибка записи в лог:", e)


print("🤖 Бот запущен")
bot.infinity_polling()
