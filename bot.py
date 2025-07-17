import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiosqlite
import os
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = '7847843904:AAHpT8Da-Von5TKMgucQfW8Q8UTKzKG5k8I'
USER_PASSWORD = 'santa2024'
ADMIN_PASSWORD = 'admin2024'

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_PATH = 'santa.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_admin INTEGER DEFAULT 0
        )''')
        await db.commit()

class RegStates(StatesGroup):
    waiting_for_password = State()

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE user_id=?', (user_id,)) as cursor:
            user = await cursor.fetchone()
    if user:
        await message.answer('Вы уже зарегистрированы!')
        return
    await message.answer('Привет! Введите пароль для регистрации:')
    await state.set_state(RegStates.waiting_for_password)

@dp.message(RegStates.waiting_for_password)
async def handle_password(message: types.Message, state: FSMContext):
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM users WHERE user_id=?', (user_id,)) as cursor:
            user = await cursor.fetchone()
        if user:
            await message.answer('Вы уже зарегистрированы!')
            await state.clear()
            return
        if text == USER_PASSWORD:
            await db.execute('INSERT INTO users (user_id, username, is_admin) VALUES (?, ?, 0)', (user_id, username))
            await db.commit()
            await message.answer('Вы успешно зарегистрированы как участник!')
            await state.clear()
        elif text == ADMIN_PASSWORD:
            await db.execute('INSERT INTO users (user_id, username, is_admin) VALUES (?, ?, 1)', (user_id, username))
            await db.commit()
            await message.answer('Вы зарегистрированы как админ! Для запуска розыгрыша используйте команду /draw')
            await state.clear()
        else:
            await message.answer('Неверный пароль. Попробуйте снова:')

@dp.message(Command('draw'))
async def cmd_draw(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, что это админ
        async with db.execute('SELECT is_admin FROM users WHERE user_id=?', (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row or row[0] != 1:
            await message.answer('Только админ может запускать розыгрыш!')
            return
        # Получаем всех участников (не админов)
        async with db.execute('SELECT user_id, username FROM users WHERE is_admin=0') as cursor:
            users = await cursor.fetchall()
        if len(users) < 2:
            await message.answer('Недостаточно участников для розыгрыша!')
            return
        # Тайный Санта: перемешиваем и распределяем
        import random
        user_ids = [u[0] for u in users]
        random.shuffle(user_ids)
        pairs = list(zip(user_ids, user_ids[1:] + user_ids[:1]))
        # Рассылаем каждому, кому он дарит
        for giver, receiver in pairs:
            async with db.execute('SELECT username FROM users WHERE user_id=?', (receiver,)) as cursor:
                receiver_row = await cursor.fetchone()
            receiver_name = receiver_row[0] if receiver_row else 'Пользователь'
            try:
                await bot.send_message(giver, f'Вы дарите подарок пользователю: @{receiver_name}')
            except Exception as e:
                await message.answer(f'Не удалось отправить сообщение пользователю {giver}: {e}')
        await message.answer('Розыгрыш завершён! Все участники получили свои пары.')

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main()) 