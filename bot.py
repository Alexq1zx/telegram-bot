import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = "8719742274:AAGPAuZxX5BXuvqrti5yV4auChHb5H51RHA"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, coins INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos (file_id TEXT, user_id INTEGER)")
conn.commit()

@dp.message(Command("start"))
async def start(msg: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?, 0)", (msg.from_user.id,))
    conn.commit()
    await msg.answer("Отправь кружок 🎥")

@dp.message(lambda m: m.video_note)
async def video(msg: types.Message):
    cursor.execute("INSERT INTO videos VALUES (?, ?)", (msg.video_note.file_id, msg.from_user.id))
    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id=?", (msg.from_user.id,))
    conn.commit()
    await msg.answer("+1 монета 💰")

@dp.message(Command("open"))
async def open(msg: types.Message):
    cursor.execute("SELECT coins FROM users WHERE user_id=?", (msg.from_user.id,))
    coins = cursor.fetchone()[0]

    if coins <= 0:
        await msg.answer("Нет монет")
        return

    cursor.execute("SELECT file_id FROM videos WHERE user_id != ?", (msg.from_user.id,))
    vids = cursor.fetchall()

    if not vids:
        await msg.answer("Нет кружков")
        return

    file_id = random.choice(vids)[0]

    cursor.execute("UPDATE users SET coins = coins - 1 WHERE user_id=?", (msg.from_user.id,))
    conn.commit()

    await msg.answer_video_note(file_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
