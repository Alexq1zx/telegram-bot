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

# таблицы
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS viewed (user_id INTEGER, video_id INTEGER)")
conn.commit()

# кнопки
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📺 Посмотреть кружок")],
        [KeyboardButton(text="💰 Мой баланс")],
        [KeyboardButton(text="📜 Условия пользования")]
    ],
    resize_keyboard=True
)

# старт
@dp.message(Command("start"))
async def start(msg: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, 0)", (msg.from_user.id,))
    conn.commit()
    await msg.answer("Отправь кружок 🎥", reply_markup=kb)

# прием кружка
@dp.message(lambda m: m.video_note)
async def video(msg: types.Message):
    cursor.execute("INSERT INTO videos (file_id, user_id) VALUES (?, ?)", (msg.video_note.file_id, msg.from_user.id))
    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id=?", (msg.from_user.id,))
    conn.commit()
    await msg.answer("+1 монета 💰")

# баланс
@dp.message(lambda m: m.text == "💰 Мой баланс")
async def balance(msg: types.Message):
    cursor.execute("SELECT coins FROM users WHERE user_id=?", (msg.from_user.id,))
    coins = cursor.fetchone()[0]
    await msg.answer(f"💰 У тебя {coins} монет")

# условия
@dp.message(lambda m: m.text == "📜 Условия пользования")
async def rules(msg: types.Message):
    await msg.answer("📜 Просто отправляй кружки и смотри чужие")

# просмотр кружка
@dp.message(lambda m: m.text == "📺 Посмотреть кружок")
async def watch(msg: types.Message):
    user_id = msg.from_user.id

    cursor.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    coins = cursor.fetchone()[0]

    if coins <= 0:
        await msg.answer("❌ Нет монет")
        return

    # берём кружки, которые пользователь ещё не видел
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

    # записываем просмотр
    cursor.execute("INSERT INTO viewed (user_id, video_id) VALUES (?, ?)", (user_id, video_id))

    # списываем монету
    cursor.execute("UPDATE users SET coins = coins - 1 WHERE user_id=?", (user_id,))
    conn.commit()

    await msg.answer_video_note(file_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
