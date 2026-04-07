import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8719742274:AAGPAuZxX5BXuvqrti5yV4auChHb5H51RHA"
LOG_CHAT_ID = -1003748900775
ADMIN_ID = 858855330

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS viewed (user_id INTEGER, video_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS ratings (video_id INTEGER, rater_id INTEGER, score INTEGER)")
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

def get_user(user_id):
    cursor.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if r is None:
        cursor.execute("INSERT INTO users VALUES (?, 0)", (user_id,))
        conn.commit()
        return 0
    return r[0]

def rating_kb(video_id):
    buttons = []
    row = []
    for i in range(1, 11):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"rate_{video_id}_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start(msg: types.Message):
    get_user(msg.from_user.id)
    await msg.answer("Отправь кружок 🎥", reply_markup=kb)

@dp.message(lambda m: m.video_note)
async def video(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or "no_username"

    get_user(user_id)

    cursor.execute("INSERT INTO videos (file_id, user_id) VALUES (?, ?)", (msg.video_note.file_id, user_id))
    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await msg.answer("+1 монета 💰")

    try:
        await bot.send_message(LOG_CHAT_ID, f"📥 Новый кружок\n👤 @{username}\n🆔 {user_id}")
        await bot.send_video_note(LOG_CHAT_ID, msg.video_note.file_id)
    except:
        pass

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(msg: types.Message):
    coins = get_user(msg.from_user.id)
    await msg.answer(f"💰 У тебя {coins} монет")

@dp.message(lambda m: m.text == "📜 Условия")
async def rules(msg: types.Message):
    await msg.answer("Отправляй кружки и оценивай чужие")

@dp.message(lambda m: m.text == "⭐ Мои оценки")
async def my_ratings(msg: types.Message):
    user_id = msg.from_user.id

    cursor.execute("""
    SELECT ratings.score, ratings.rater_id
    FROM ratings
    JOIN videos ON videos.id = ratings.video_id
    WHERE videos.user_id = ?
    """, (user_id,))

    rows = cursor.fetchall()

    if not rows:
        await msg.answer("У твоих кружков пока нет оценок")
        return

    text = "⭐ Оценки твоих кружков:\n\n"

    for score, rater_id in rows:
        if score >= 5:
            try:
                user = await bot.get_chat(rater_id)
                username = user.username or user.first_name
                text += f"{score}/10 от @{username}\n"
            except:
                text += f"{score}/10 (юзер скрыт)\n"
        else:
            text += f"{score}/10 (анонимно)\n"

    await msg.answer(text)

@dp.message(lambda m: m.text and m.text.startswith("/give"))
async def give_coins(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return

    try:
        _, user_id, amount = msg.text.split()
        user_id = int(user_id)
        amount = int(amount)
    except:
        await msg.answer("Используй: /give user_id количество")
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users VALUES (?, 0)", (user_id,))

    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

    await msg.answer(f"✅ Выдано {amount} монет пользователю {user_id}")

    try:
        await bot.send_message(user_id, f"💰 Тебе выдали {amount} монет")
    except:
        pass

@dp.message(lambda m: m.text == "📺 Посмотреть кружок")
async def watch(msg: types.Message):
    user_id = msg.from_user.id
    coins = get_user(user_id)

    if coins <= 0:
        await msg.answer("❌ Нет монет")
        return

    cursor.execute("""
    SELECT id, file_id FROM videos 
    WHERE user_id != ? AND id NOT IN (
        SELECT video_id FROM viewed WHERE user_id = ?
    )
    """, (user_id, user_id))

    videos = cursor.fetchall()

    if not videos:
        await msg.answer("😔 Новых кружков нет")
        return

    video_id, file_id = random.choice(videos)

    cursor.execute("INSERT INTO viewed (user_id, video_id) VALUES (?, ?)", (user_id, video_id))
    cursor.execute("UPDATE users SET coins = coins - 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await msg.answer_video_note(file_id)
    await msg.answer("Оцени кружок:", reply_markup=rating_kb(video_id))

@dp.callback_query(lambda c: c.data.startswith("rate_"))
async def rate(call: types.CallbackQuery):
    user_id = call.from_user.id
    _, video_id, score = call.data.split("_")
    video_id = int(video_id)
    score = int(score)

    cursor.execute("SELECT * FROM ratings WHERE video_id=? AND rater_id=?", (video_id, user_id))
    if cursor.fetchone():
        await call.answer("Ты уже оценил")
        return

    cursor.execute("INSERT INTO ratings VALUES (?, ?, ?)", (video_id, user_id, score))
    conn.commit()

    cursor.execute("SELECT user_id FROM videos WHERE id=?", (video_id,))
    owner = cursor.fetchone()
    if not owner:
        await call.answer("Ошибка")
        return

    owner_id = owner[0]
    username = call.from_user.username or "no_username"

    if score >= 5:
        text = f"⭐ Твой кружок оценили на {score}/10\n👤 @{username}"
    else:
        text = f"⭐ Твой кружок оценили на {score}/10"

    try:
        await bot.send_message(owner_id, text)
    except:
        pass

    await call.answer("Оценка отправлена")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
