import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8719742274:AAGPAuZxX5BXuvqrti5yV4auChHb5H51RHA"
LOG_CHAT_ID = -1003748900775
ADMIN_ID = 858855330
CHANNEL_ID = "@tinleo"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS viewed (user_id INTEGER, video_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS ratings (video_id INTEGER, rater_id INTEGER, score INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY)")
conn.commit()

cursor.execute("PRAGMA table_info(videos)")
columns = [col[1] for col in cursor.fetchall()]
if "active" not in columns:
    cursor.execute("ALTER TABLE videos ADD COLUMN active INTEGER DEFAULT 1")
    conn.commit()

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📺 Посмотреть кружок")],
        [KeyboardButton(text="💰 Мой баланс")],
        [KeyboardButton(text="⭐ Мои оценки")],
        [KeyboardButton(text="📜 Условия")]
    ],
    resize_keyboard=True
)

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/tinleo")],
        [InlineKeyboardButton(text="✅ Проверить", callback_data="check_sub")]
    ])

async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

def is_banned(user_id):
    cursor.execute("SELECT 1 FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def get_user(user_id):
    cursor.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if r is None:
        cursor.execute("INSERT INTO users VALUES (?, 0)", (user_id,))
        conn.commit()
        return 0
    return r[0]

def rating_kb(video_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"rate_{video_id}_{i}") for i in range(1,6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"rate_{video_id}_{i}") for i in range(6,11)]
    ])

async def banned_msg(msg):
    await msg.answer("🚫 Вы заблокированы\nОбжаловать — @HETyMOHET")

@dp.message(Command("start"))
async def start(msg: types.Message):
    if is_banned(msg.from_user.id):
        await banned_msg(msg)
        return
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Подпишись на канал", reply_markup=sub_kb())
        return
    get_user(msg.from_user.id)
    await msg.answer("Отправь кружок 🎥", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub_btn(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.answer("✅ Доступ открыт", reply_markup=kb)
    else:
        await call.answer("❌ Ты не подписан", show_alert=True)

@dp.message(lambda m: m.video_note)
async def video(msg: types.Message):
    if is_banned(msg.from_user.id):
        await banned_msg(msg)
        return
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Подпишись", reply_markup=sub_kb())
        return

    user_id = msg.from_user.id
    username = msg.from_user.username or "no_username"

    get_user(user_id)

    cursor.execute("INSERT INTO videos (file_id, user_id, active) VALUES (?, ?, 1)", (msg.video_note.file_id, user_id))
    video_id = cursor.lastrowid

    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await msg.answer("+1 монета 💰")

    try:
        await bot.send_message(LOG_CHAT_ID, f"📥 Кружок\n👤 @{username}\n🆔 {user_id}\n🎥 ID кружка: {video_id}")
        await bot.send_video_note(LOG_CHAT_ID, msg.video_note.file_id)
    except:
        pass

@dp.message(lambda m: m.text == "📺 Посмотреть кружок")
async def watch(msg: types.Message):
    if is_banned(msg.from_user.id):
        await banned_msg(msg)
        return
    if not await check_sub(msg.from_user.id):
        await msg.answer("❗ Подпишись", reply_markup=sub_kb())
        return

    user_id = msg.from_user.id
    coins = get_user(user_id)

    if coins <= 0:
        await msg.answer("❌ Нет монет")
        return

    cursor.execute("""
    SELECT id, file_id FROM videos 
    WHERE active=1 AND user_id != ? AND id NOT IN (
        SELECT video_id FROM viewed WHERE user_id = ?
    )
    """, (user_id, user_id))

    videos = cursor.fetchall()

    if not videos:
        await msg.answer("😔 Нет новых кружков")
        return

    video_id, file_id = random.choice(videos)

    cursor.execute("INSERT INTO viewed VALUES (?, ?)", (user_id, video_id))
    cursor.execute("UPDATE users SET coins = coins - 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await msg.answer_video_note(file_id)
    await msg.answer("Оцени кружок:", reply_markup=rating_kb(video_id))

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(msg: types.Message):
    if is_banned(msg.from_user.id):
        await banned_msg(msg)
        return
    coins = get_user(msg.from_user.id)
    await msg.answer(f"💰 У тебя {coins} монет")

@dp.message(lambda m: m.text == "⭐ Мои оценки")
async def my_ratings(msg: types.Message):
    if is_banned(msg.from_user.id):
        await banned_msg(msg)
        return

    user_id = msg.from_user.id
    cursor.execute("""
    SELECT ratings.score, ratings.rater_id
    FROM ratings
    JOIN videos ON videos.id = ratings.video_id
    WHERE videos.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()

    if not rows:
        await msg.answer("Нет оценок")
        return

    text = ""
    for score, rater_id in rows:
        if score >= 5:
            try:
                user = await bot.get_chat(rater_id)
                username = user.username or user.first_name
                text += f"{score}/10 от @{username}\n"
            except:
                text += f"{score}/10\n"
        else:
            text += f"{score}/10 (анонимно)\n"

    await msg.answer(text)

@dp.message(lambda m: m.text and m.text.startswith("/give"))
async def give_coins(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    _, user_id, amount = msg.text.split()
    user_id = int(user_id)
    amount = int(amount)

    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

    await msg.answer("Выдано")

@dp.message(lambda m: m.text and m.text.startswith("/ban"))
async def ban(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    user_id = int(msg.text.split()[1])
    cursor.execute("INSERT OR IGNORE INTO banned VALUES (?)", (user_id,))
    conn.commit()

    try:
        await bot.send_message(user_id, "🚫 Вы заблокированы\nОбжаловать — @HETyMOHET")
    except:
        pass

    await msg.answer("Забанен")

@dp.message(lambda m: m.text and m.text.startswith("/unban"))
async def unban(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    user_id = int(msg.text.split()[1])
    cursor.execute("DELETE FROM banned WHERE user_id=?", (user_id,))
    conn.commit()

    try:
        await bot.send_message(user_id, "✅ Ваш аккаунт разблокирован")
    except:
        pass

    await msg.answer("Разбанен")

@dp.message(lambda m: m.text and m.text.startswith("/delete"))
async def delete_video(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    video_id = int(msg.text.split()[1])

    cursor.execute("SELECT user_id FROM videos WHERE id=?", (video_id,))
    res = cursor.fetchone()

    if not res:
        await msg.answer("Не найден")
        return

    owner_id = res[0]

    cursor.execute("UPDATE videos SET active=0 WHERE id=?", (video_id,))
    conn.commit()

    try:
        await bot.send_message(owner_id, "Твой кружок не подходит")
    except:
        pass

    await msg.answer("Удалено")

@dp.callback_query(lambda c: c.data.startswith("rate_"))
async def rate(call: types.CallbackQuery):
    user_id = call.from_user.id
    _, video_id, score = call.data.split("_")

    cursor.execute("INSERT INTO ratings VALUES (?, ?, ?)", (video_id, user_id, score))
    conn.commit()

    await call.answer("Оценено")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
