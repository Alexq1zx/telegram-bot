import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "8719742274:AAGPAuZxX5BXuvqrti5yV4auChHb5H51RHA"

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id TEXT,
    username TEXT,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    user_id INTEGER,
    video_id INTEGER,
    PRIMARY KEY (user_id, video_id)
)
""")

conn.commit()

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎲 Открыть кружок", callback_data="open"))
    return kb

def rate_kb(video_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("👍", callback_data=f"like_{video_id}"),
        InlineKeyboardButton("👎", callback_data=f"dislike_{video_id}")
    )
    return kb

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
    conn.commit()
    await msg.answer("Отправь кружок 🎥 и получи монету!", reply_markup=main_menu())

@dp.message_handler(content_types=types.ContentType.VIDEO_NOTE)
async def handle_video(msg: types.Message):
    user_id = msg.from_user.id
    file_id = msg.video_note.file_id

    username = msg.from_user.username
    full_name = msg.from_user.full_name
    display_name = f"@{username}" if username else full_name

    cursor.execute(
        "INSERT INTO videos (user_id, file_id, username) VALUES (?, ?, ?)",
        (user_id, file_id, display_name)
    )

    cursor.execute("UPDATE users SET coins = coins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    await msg.answer("🔥 Кружок сохранён! +1 монета", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: c.data == "open")
async def open_video(call: types.CallbackQuery):
    user_id = call.from_user.id

    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    coins = cursor.fetchone()[0]

    if coins <= 0:
        await call.message.answer("❌ Нет монет")
        return

    cursor.execute("""
    SELECT id, file_id, username FROM videos 
    WHERE user_id != ?
    """, (user_id,))
    videos = cursor.fetchall()

    if not videos:
        await call.message.answer("😔 Пока нет кружков")
        return

    video_id, file_id, username = random.choice(videos)

    cursor.execute("UPDATE users SET coins = coins - 1 WHERE user_id = ?", (user_id,))
    conn.commit()

    await bot.send_video_note(call.message.chat.id, file_id)

    await bot.send_message(
        call.message.chat.id,
        f"👤 Автор: {username}"
    )

    await bot.send_message(
        call.message.chat.id,
        "Оцени кружок 👇",
        reply_markup=rate_kb(video_id)
    )

@dp.callback_query_handler(lambda c: c.data.startswith("like_") or c.data.startswith("dislike_"))
async def rate(call: types.CallbackQuery):
    user_id = call.from_user.id
    action, video_id = call.data.split("_")
    video_id = int(video_id)

    cursor.execute("SELECT * FROM votes WHERE user_id=? AND video_id=?", (user_id, video_id))
    if cursor.fetchone():
        await call.answer("Ты уже голосовал 😎", show_alert=True)
        return

    if action == "like":
        cursor.execute("UPDATE videos SET likes = likes + 1 WHERE id=?", (video_id,))
    else:
        cursor.execute("UPDATE videos SET dislikes = dislikes + 1 WHERE id=?", (video_id,))

    cursor.execute("INSERT INTO votes (user_id, video_id) VALUES (?, ?)", (user_id, video_id))
    conn.commit()

    await call.answer("Голос учтён 🔥")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
