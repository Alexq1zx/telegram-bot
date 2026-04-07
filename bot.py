import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = "8719742274:AAGPAuZxX5BXuvqrti5yV4auChHb5H51RHA"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS viewed (user_id INTEGER, video_id INTEGER)")
conn.commit()

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📺 Посмотреть кружок")],
        [KeyboardButton(text="💰 Мой баланс")],
        [KeyboardButton(text="📜 Условия пользования")]
    ],
    resize_keyboard=True
)

def get_user(user_id):
    cursor.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users VALUES (?, 0)", (user_id,))
        conn.commit()
        return 0
    return result[0]

@dp.message(Command("start"))
async def start(msg: types.Message):
    get_user(msg.from_user.id)
    await msg.answer("Отправь кружок 🎥", reply_markup=kb)

@dp.message(lambda m: m.video_note)
async def video(msg: types.Message):
    user_id = msg.from_user.id
    get_user(user_id)
    cursor.execute("INSERT INTO videos (file_id, user_id) VALUES (?, ?)", (msg.video_note.file_id, user_id))
    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    await msg.answer("+1 монета 💰")

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(msg: types.Message):
    coins = get_user(msg.from_user.id)
    await msg.answer(f"💰 У тебя {coins} монет")

@dp.message(lambda m: m.text == "📜 Условия пользования")
async def rules(msg: types.Message):
    await msg.answer("📜 Просто отправляй кружки и смотри чужие")

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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
