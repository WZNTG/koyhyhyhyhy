import asyncio
import sqlite3
import random
import time
from aiogram import Bot, Dispatcher, types, F, html
from aiogram.enums import ChatType

# --- ОБНОВЛЕННЫЕ ДАННЫЕ ---
TOKEN = "8542233717:AAEfuFgvdkHLRDMshwzWq885r2dECOiYW0s"
ADMIN_ID = 5394084759

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def db_query(sql, params=(), fetchall=False, commit=False):
    with sqlite3.connect('chaihana.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if commit: conn.commit()
        if fetchall: return cursor.fetchall()
        return cursor.fetchone()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users 
                (user_id INTEGER, chat_id INTEGER, name TEXT, score INTEGER DEFAULT 0, last INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id))''', commit=True)
    db_query('''CREATE TABLE IF NOT EXISTS promos 
                (code TEXT PRIMARY KEY, bonus INTEGER, uses INTEGER)''', commit=True)
    db_query('''CREATE TABLE IF NOT EXISTS used_promos 
                (user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))''', commit=True)

def get_user_rank(user_id, chat_id):
    results = db_query("SELECT user_id FROM users WHERE chat_id = ? ORDER BY score DESC", (chat_id,), fetchall=True)
    for index, row in enumerate(results, 1):
        if row[0] == user_id:
            return index
    return 1

# Функция для красивого вывода оставшегося времени
def get_time_left(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}ч. {minutes}м. {secs}с."

# --- ОБРАБОТЧИК ---

@dp.message(F.text)
async def handle_all_messages(msg: types.Message):
    text = msg.text.lower().strip()
    user_id = msg.from_user.id
    chat_id = msg.chat.id
    user_full_name = msg.from_user.full_name

    # КОМАНДА: ЧАЙХАНА
    if text == "чайхана":
        if msg.chat.type == ChatType.PRIVATE:
            return await msg.answer("Команда работает только в чатах!")

        user = db_query("SELECT score, last FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        now = int(time.time())
        
        # Проверка времени (24 часа = 86400 секунд)
        if user and now - user[1] < 86400:
            time_left = 86400 - (now - user[1])
            return await msg.reply(f"Следующая попытка через {get_time_left(time_left)}.")

        change = random.choice([i for i in range(-5, 11) if i != 0])
        current_score = user[0] if user else 0
        new_score = current_score + change
        
        db_query("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)", 
                 (user_id, chat_id, user_full_name, new_score, now), commit=True)
        
        rank = get_user_rank(user_id, chat_id)
        word = "выросла" if change > 0 else "упала"
        
        res_text = (
            f"{user_full_name}, твоя преданность чайхане {word} на {abs(change)} очков.\n"
            f"Теперь она равна {new_score} очков.\n"
            f"Ты занимаешь {rank} место в топе\n"
            f"Следующая попытка завтра!"
        )
        await msg.answer(res_text)

    # КОМАНДА: ТОП
    elif text == "топ":
        if msg.chat.type == ChatType.PRIVATE:
            return await msg.answer("Топ доступен только в чатах.")
        top = db_query("SELECT name, score FROM users WHERE chat_id = ? ORDER BY score DESC LIMIT 10", (chat_id,), fetchall=True)
        if not top: return await msg.answer("Топ пуст.")
        res = "Топ чата:\n" + "\n".join([f"{i}. {n} — {s}" for i, (n, s) in enumerate(top, 1)])
        await msg.answer(res)

    # КОМАНДА: МИР / ГЛОБАЛ
    elif text in ["мир", "глобал"]:
        top = db_query("SELECT name, SUM(score) as s FROM users GROUP BY user_id ORDER BY s DESC LIMIT 10", fetchall=True)
        res = "Мировой топ:\n" + "\n".join([f"{i}. {n} — {s}" for i, (n, s) in enumerate(top, 1)])
        await msg.answer(res)

    # КОМАНДА: ЮЗАТЬ (В ЛС)
    elif text.startswith("юзать"):
        if msg.chat.type != ChatType.PRIVATE:
            try: await msg.delete()
            except: pass
            return await msg.answer("Активация промокодов только в ЛС бота!")

        try:
            code = msg.text.split()[1]
            already = db_query("SELECT 1 FROM used_promos WHERE user_id = ? AND code = ?", (user_id, code))
            if already:
                return await msg.answer("Ты уже активировал этот код!")

            p = db_query("SELECT bonus, uses FROM promos WHERE code = ?", (code,))
            if p and p[1] > 0:
                db_query("UPDATE promos SET uses = uses - 1 WHERE code = ?", (code,), commit=True)
                db_query("INSERT INTO used_promos VALUES (?, ?)", (user_id, code), commit=True)
                db_query("UPDATE users SET score = score + ? WHERE user_id = ?", (p[0], user_id), commit=True)
                await msg.answer(f"Добавлено {p[0]} очков преданности!")
            else:
                await msg.answer("Код не найден или закончился.")
        except: pass

    # КОМАНДА: ПРОМИК (АДМИН)
    elif text.startswith("промик"):
        if user_id != ADMIN_ID: return
        try:
            _, code, bonus, count = msg.text.split()
            db_query("INSERT OR REPLACE INTO promos VALUES (?, ?, ?)", (code, int(bonus), int(count)), commit=True)
            await msg.answer(f"Код {code} на {bonus} очков создан.")
        except: pass

async def main():
    init_db()
    print("Чайхана запущена с новым токеном!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())