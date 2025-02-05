import asyncio
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

API_TOKEN = '7674744195:AAHiJC9P6MHaz3fphQv567Qi5q12IHLfyIQ'
GROUP_ID = -1002431710497 # tut id gruppy
STORAGE_FILE = 'user_topics.json' # tut save data

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

user_topics = {}
topic_users = {}
message_counters = {}

async def load_data():
    try:
        with open(STORAGE_FILE, 'r') as f:
            data = json.load(f)
            return {int(k): v for k, v in data.get('user_topics', {}).items()}, \
                   {int(k): v for k, v in data.get('topic_users', {}).items()}
    except FileNotFoundError:
        return {}, {}

async def save_data():
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump({
                'user_topics': {str(k): v for k, v in user_topics.items()},
                'topic_users': {str(k): v for k, v in topic_users.items()}
            }, f, indent=2)
    except Exception as e:
        await bot.send_message(GROUP_ID, f"❌ Ошибка сохранения данных: {e}")

@dp.message(Command('start'))
async def start(message: Message):
    await message.answer(
        "👋 Здравствуйте! Опишите вашу проблему или задайте вопрос. "
        "Мы постараемся ответить как можно скорее."
    )

@dp.message(F.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id
    
    try:
        if user_id in user_topics:
            try:
                await bot.get_chat(GROUP_ID)
                await message.copy_to(
                    chat_id=GROUP_ID,
                    message_thread_id=user_topics[user_id]
                )
            except Exception as e:
                if "message thread not found" in str(e).lower():
                    del user_topics[user_id]
                    for topic_id, uid in list(topic_users.items()):
                        if uid == user_id:
                            del topic_users[topic_id]
                    await save_data()
                    return await handle_private_message(message)
                await bot.send_message(GROUP_ID, f"❌ Ошибка при пересылке сообщения: {e}")
                raise e
        else:
            username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
            current_time = message.date.strftime("%d.%m.%Y %H:%M")
            topic = await bot.create_forum_topic(
                chat_id=GROUP_ID,
                name=f"💬 {username} | {current_time}"
            )
            user_topics[user_id] = topic.message_thread_id
            topic_users[topic.message_thread_id] = user_id
            await save_data()
            
            await bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=topic.message_thread_id,
                text=f"📝 Новое обращение:\nПользователь: {username}\nID: {user_id}"
            )
            await message.copy_to(
                chat_id=GROUP_ID,
                message_thread_id=topic.message_thread_id
            )

        message_counters[user_id] = message_counters.get(user_id, 0) + 1
        
        if message_counters[user_id] == 1:
            await message.reply("✅ Ваше сообщение получено. Ожидайте ответа администратора.")
        elif message_counters[user_id] % 3 == 0:
            await message.reply("✅ Сообщение передано администратору.") # tut mozhno dobavit' chto-to tipa "если у вас есть еще вопросы, задавайте"

    except Exception as e:
        await bot.send_message(GROUP_ID, f"❌ Ошибка обработки сообщения: {e}")
        await message.reply("❌ Произошла ошибка. Пожалуйста, попробуйте позже.") 

@dp.message(F.chat.id == GROUP_ID)
async def handle_group_message(message: Message):
    if not message.message_thread_id or message.from_user.is_bot:
        return

    try:
        user_id = topic_users.get(message.message_thread_id)
        if not user_id:
            return

        text = message.text or message.caption
        if text:
            await bot.send_message(
                chat_id=user_id,
                text=f"👨‍💼 Ответ поддержки:\n\n{text}" # sex sex sex
            )
        
        if message.photo:
            await bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id)
        elif message.video:
            await bot.send_video(chat_id=user_id, video=message.video.file_id)
        elif message.document:
            await bot.send_document(chat_id=user_id, document=message.document.file_id)
        elif message.voice:
            await bot.send_voice(chat_id=user_id, voice=message.voice.file_id)
            
    except Exception as e:
        await bot.send_message(GROUP_ID, f"❌ Ошибка отправки ответа: {e}")

async def main():
    global user_topics, topic_users
    user_topics, topic_users = await load_data()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())