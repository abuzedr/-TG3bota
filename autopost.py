import uuid
# predlozhka
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import json
import re

from telegram import CallbackQuery
from db import Database

def clean_city_name(text: str) -> str:
    emojis = ['🌆', '🌅', '🌇', '🏙', '🌃']
    for emoji in emojis:
        text = text.replace(emoji, ' ')
    return ' '.join(word for word in text.split() if word)

TOKEN = "8106342610:AAFzjuE9HNWd61BjuctKvrTvwCx4d5QSpJU"
MODERGROUP_ID = "-1002336497511"  # gruppa moderov
POST_DELAY = 10  # zaderjka v minutah kogda send post

CITIES = {  # id chatov
    "Пермь": "-1002465850721",
    "Владивосток": "-1002366538502",
    "Казань": "-1002236351628",
    "Краснодар": "-1002324263770",
    "Саратов": "-1002325766806"
}

class PostStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_content = State()
    waiting_for_confirmation = State()
    waiting_for_custom_time = State()
    waiting_for_delay_date = State()
    waiting_for_delete_confirm = State()

def get_city_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌆 Пермь"), KeyboardButton(text="🌅 Владивосток")],
            [KeyboardButton(text="🌇 Казань"), KeyboardButton(text="🏙 Краснодар")],
            [KeyboardButton(text="🌃 Саратов")]
        ],
        resize_keyboard=True
    )
def get_moderation_keyboard(post_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"accept_{post_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{post_id}")
            ],
            [InlineKeyboardButton(text="⏳ Отложить", callback_data=f"delay_{post_id}")]
        ]
    )

def get_new_post_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать новый пост")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_post"),
            InlineKeyboardButton(text="🔄 Изменить", callback_data="edit_post")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_post")]
    ])

def get_delay_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delay")]
        ]
    )

def get_delay_date_keyboard():
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    day_after_tomorrow = today + timedelta(days=2)
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📅 Сегодня ({today.strftime('%d.%m')})", callback_data="delay_today")],
            [InlineKeyboardButton(text=f"📅 Завтра ({tomorrow.strftime('%d.%m')})", callback_data="delay_tomorrow")],
            [InlineKeyboardButton(text=f"📅 Послезавтра ({day_after_tomorrow.strftime('%d.%m')})", callback_data="delay_day_after_tomorrow")],
            [InlineKeyboardButton(text="🗓 Выбрать дату", callback_data="delay_custom_date")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delay")]
        ]
    )

def get_time_keyboard(selected_date):
    buttons = []
    for hour in range(24):
        buttons.append([
            InlineKeyboardButton(
                text=f"🕐 {hour:02d}:00",
                callback_data=f"delay_time_{selected_date.isoformat()}_{hour:02d}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delay")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_username(user) -> str:
    if user or user.username:
        return f"@{user.username}"
    return user.full_name if user else "Unknown"

def get_after_post_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Еще один пост")],
            [KeyboardButton(text="✅ Завершить")]
        ],
        resize_keyboard=True
    )

def get_final_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/start")]
        ],
        resize_keyboard=True
    )

def get_post_keyboard(page: int, total_pages: int):
    buttons = []
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"page_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"page_{page+1}"))
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

class UserState:
    def __init__(self):
        self.users = {}  # user_id: username

    def add_user(self, user_id: int, username: str):
        self.users[user_id] = username

    def get_user_id(self, username: str) -> int:
        for user_id, stored_username in self.users.items():
            if stored_username == username:
                return user_id
        return None

class PostBot:
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.scheduled_posts = []
        self.temp_post_data = {}
        self.post_ids = {}
        self.load_posts()
        self.setup_handlers()
        self.posts_per_page = 5  #  ce per page in /del
        self.user_state = UserState()
        self.db = Database()

    def load_posts(self):
        try:
            with open('scheduled_posts.json', 'r') as f:
                self.scheduled_posts = json.load(f)
        except FileNotFoundError:
            pass

    def save_posts(self):
        with open('scheduled_posts.json', 'w') as f:
            json.dump(self.scheduled_posts, f, indent=2)

    def setup_handlers(self):

        self.dp.message.register(self.cmd_start, Command("start"))
        

        self.dp.message.register(
            self.process_city_selection,
            lambda message: message.text and any(city in clean_city_name(message.text) for city in CITIES.keys())
        )
        

        self.dp.message.register(
            self.handle_post, 
            PostStates.waiting_for_content
        )
        

        self.dp.callback_query.register(
            self.process_post_confirmation,
            lambda c: c.data in ['confirm_post', 'edit_post', 'cancel_post']
        )
        

        self.dp.callback_query.register(
            self.process_moderation, 
            lambda c: c.data or c.data.startswith(('accept_', 'reject_', 'delay_'))
        )

        self.dp.callback_query.register(
            self.process_delay_time,
            lambda c: c.data and (
                c.data.startswith(('delay_time_', 'delay_today', 'delay_tomorrow', 'delay_day_after_tomorrow')) or 
                c.data in ['cancel_delay', 'delay_custom_date']
            )
        )


        self.dp.message.register(
            self.handle_another_post,
            lambda message: message.text == "📝 Еще один пост"
        )
        

        self.dp.message.register(
            self.handle_finish,
            lambda message: message.text == "✅ Завершить"
        )

        self.dp.message.register(
            self.cmd_start,
            Command("start")
        )
        self.dp.message.register(
            self.handle_custom_time,
            PostStates.waiting_for_custom_time
        )

        self.dp.message.register(
            self.cmd_delete,
            Command("del")
        )
        self.dp.callback_query.register(
            self.process_delete_confirmation,
            lambda c: c.data.startswith('delete_')
        )


        self.dp.callback_query.register(
            self.process_page_navigation,
            lambda c: c.data.startswith('page_')
        )

        self.dp.message.register(
            self.handle_message,
            lambda message: message.text and message.text.startswith('/del_')
        )

    async def cmd_start(self, message: types.Message, state: FSMContext):
        welcome_text = (
            "👋 Добро пожаловать в систему публикации постов!\n\n"
            "🌆 Выберите город для публикации вашего поста:\n"
            "📝 После выбора города вы сможете отправить:\n"
            "- Текст\n"
            "- Фото\n"
            "- Видео\n"
            "- GIF-анимации\n\n"
            "❗️ Ваш пост будет отправлен на модерацию"
        )
        await message.answer(welcome_text, reply_markup=get_city_keyboard())
        await state.set_state(PostStates.waiting_for_city)

    async def cmd_cancel(self, message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "❌ Действие отменено. Нажмите /start для начала работы.",
            reply_markup=get_new_post_keyboard()
        )

    async def handle_cancel(self, message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "❌ Действие отменено. Нажмите /start для начала работы.",
            reply_markup=get_new_post_keyboard()
        )

    async def process_city_selection(self, message: types.Message, state: FSMContext):
        if not message.text:
            return
            
        clean_text = clean_city_name(message.text)
        city = next((city for city in CITIES.keys() if city in clean_text), None)
        if not city:
            await message.answer(
                "❌ Выберите город из списка",
                reply_markup=get_city_keyboard()
            )
            return
            
        await state.update_data(city=city)
        await message.answer(
            f"🎯 Выбран город: {city}\n\n"
            f"📤 Теперь отправьте ваш пост\n"
            f"Поддерживаемые форматы:\n"
            f"📝 Текст\n"
            f"🖼 Фото\n"
            f"🎥 Видео\n"
            f"🎭 GIF"
        )
        await state.set_state(PostStates.waiting_for_content)

    async def handle_post(self, message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if (current_state != PostStates.waiting_for_content and
            current_state != PostStates.waiting_for_custom_time):
            return
            
        data = await state.get_data()
        city = data.get('city')
        if not city:
            await message.answer(
                "❌ Сначала выберите город",
                reply_markup=get_city_keyboard()
            )
            return

        user_info = format_username(message.from_user)

        try:
            preview_text = "📋 Предпросмотр вашего поста:\n\n"
            if message.photo:
                preview = await message.copy_to(message.from_user.id)
                preview_text += message.caption or ""
            elif message.video:
                preview = await message.copy_to(message.from_user.id)
                preview_text += message.caption or ""
            elif message.animation:
                preview = await message.copy_to(message.from_user.id)
                preview_text += message.caption or ""
            else:
                preview_text += message.text or ""
                preview = await message.answer(preview_text)
            await state.update_data(
                message_id=message.message_id,
                preview_message_id=preview.message_id,
                content_type=message.content_type,
                file_id=message.photo[-1].file_id if message.photo else 
                       message.video.file_id if message.video else
                       message.animation.file_id if message.animation else None,
                caption=message.caption,
                text=message.text
            )

            confirm_message = (
                f"🔍 Проверьте ваш пост выше\n\n"
                f"📍 Город публикации: {city}\n"
                f"👤 Автор: {user_info}\n\n"
                f"Всё верно?"
            )
            
            await message.answer(confirm_message, reply_markup=get_confirm_keyboard())
            await state.set_state(PostStates.waiting_for_confirmation)

        except Exception as e:
            await message.answer("❌ Ошибка при отправке. Попробуйте снова.")

    async def process_post_confirmation(self, callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        
        if callback.data == "confirm_post":
            try:
                self.user_state.add_user(
                    callback.from_user.id,
                    callback.from_user.username or str(callback.from_user.id)
                )
                
                sent = None
                if data.get('content_type') in ['photo', 'video', 'animation']:
                    method = getattr(self.bot, f"send_{data['content_type']}")

                    sent = await method(
                        MODERGROUP_ID,
                        data['file_id'],
                        caption=data.get('caption', '')
                    )
                else:
                    sent = await self.bot.send_message(
                        MODERGROUP_ID,
                        data.get('text', '')
                    )

                post_id = str(uuid.uuid4().hex[:8])

                moderation_text = (
                    f"📝 Пост на проверку ⬆️ | ID: {post_id}\n\n"
                    f"🏙 Город: {data['city']}\n"
                    f"👤 Пользователь: {format_username(callback.from_user)}"
                )

                await self.bot.send_message(
                    MODERGROUP_ID,
                    moderation_text,
                    reply_markup=get_moderation_keyboard(str(sent.message_id)),
                    reply_to_message_id=sent.message_id
                )

                await callback.message.edit_text(
                    "✅ Пост отправлен на модерацию. Ожидайте решения.",
                    reply_markup=None
                )
            
                await self.bot.send_message(
                    callback.from_user.id,
                    "Что хотите сделать дальше?",
                    reply_markup=get_after_post_keyboard()
                )

            except Exception as e:
                await callback.message.edit_text(
                    "❌ Ошибка при отправке. Попробуйте снова.",
                    reply_markup=None
                )

        elif callback.data == "edit_post":
            await callback.message.edit_text(
                "📝 Отправьте новый вариант поста:",
                reply_markup=None
            )
            await state.set_state(PostStates.waiting_for_content)

        elif callback.data == "cancel_post":
            await callback.message.edit_text(
                "❌ Публикация отменена. Нажмите /start для создания нового поста.",
                reply_markup=None
            )
            await state.clear()

        await callback.answer(show_alert=False)

    async def process_moderation(self, callback: types.CallbackQuery, state: FSMContext):
        try:
            action, message_id = callback.data.split('_', 1)

            # Получаем ID поста из текста сообщения
            original_post_id = next((line.split('ID:')[1].strip() 
                              for line in callback.message.text.split('\n') 
                              if 'ID:' in line), None)

            message_text = callback.message.text
            city = None
            username = None
            for line in message_text.split('\n'):
                if "Город:" in line:
                    city = line.split('Город:')[1].strip()
                elif "Пользователь:" in line:
                    username = line.split('Пользователь:')[1].strip()
                    username = username.lstrip('@')

            if not city:
                await callback.answer("Ошибка: не удалось определить город", show_alert=True)
                return

            try:
                if username:
                    user_id = self.user_state.get_user_id(username)
                    if user_id:
                        if action == 'accept':
                            notification = "✅ Ваш пост одобрен и будет опубликован!"
                        elif action == 'reject':
                            notification = "❌ Ваш пост был отклонен модератором."
                        elif action == 'delay':
                            notification = "⏳ Ваш пост будет опубликован позже."
                        
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=notification
                        )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {username}: {e}")

            if action == 'delay':
                self.temp_post_data = {
                    'post_id': original_post_id,  # Сохраняем оригинальный ID поста
                    'message_id': message_id,  # ID сообщения для копирования
                    'message': callback.message.text,
                    'city': city,
                    'approved_by': format_username(callback.from_user),
                    'original_markup': callback.message.reply_markup,
                    'chat_id': callback.message.chat.id
                }
                await callback.message.edit_text(
                    "⏰ Введите время публикации в формате ЧЧ:ММ (например, 14:30)\n\n"
                    "❗️ Пост будет опубликован:\n"
                    "- Сегодня, если время больше текущего\n"
                    "- Завтра, если время меньше текущего\n\n"
                    "Для отмены нажмите кнопку ниже:",
                    reply_markup=get_delay_keyboard()
                )
                await state.set_state(PostStates.waiting_for_custom_time)
                return

            if action == 'accept':
                last_time = datetime.now()
                if self.scheduled_posts:
                    last_time = datetime.fromisoformat(self.scheduled_posts[-1]['scheduled_time'])
                
                publish_time = max(datetime.now(), last_time + timedelta(minutes=POST_DELAY))
                
                new_post_id = str(uuid.uuid4().hex[:8])
                post_data = {
                    'post_id': new_post_id,
                    'message_id': message_id,  # ID сообщения для копирования
                    'chat_id': callback.message.chat.id,
                    'scheduled_time': publish_time.isoformat(),
                    'city': city,
                    'approved_by': format_username(callback.from_user),
                    'status': 'approved',
                    'content': callback.message.text
                }

                self.db.add_post(post_data)
                
                original_text = callback.message.text
                await callback.message.edit_text(
                    f"✅ Пост будет опубликован в {publish_time.strftime('%H:%M %d.%m.%Y')}\n\n"
                    f"{original_text}\n\n"
                    f"👤 Одобрил: {format_username(callback.from_user)}\n"
                    f"🆔 ID поста: {new_post_id}"
                )

            elif action == 'reject':
                await callback.message.edit_text(
                    f"❌ Пост отклонен\n\n"
                    f"{callback.message.text}\n\n"
                    f"👤 Отклонил: {format_username(callback.from_user)}"
                )

        except Exception as e:
            print(f"Ошибка в process_moderation: {str(e)}")
            await callback.message.answer(f"❌ Ошибка при обработке: {str(e)}")
        
        await callback.answer(show_alert=False)

    async def process_delay_time(self, callback: types.CallbackQuery, state: FSMContext):
        try:
            if callback.data == 'cancel_delay':
                await callback.message.edit_text(
                    self.temp_post_data['message'],
                    reply_markup=get_moderation_keyboard(self.temp_post_data['post_id'])
                )
                return

            if callback.data in ['delay_today', 'delay_tomorrow', 'delay_day_after_tomorrow']:
                selected_date = datetime.now().date()
                if callback.data == 'delay_tomorrow':
                    selected_date += timedelta(days=1)
                elif callback.data == 'delay_day_after_tomorrow':
                    selected_date += timedelta(days=2)

                await callback.message.edit_text(
                    f"⏰ Выберите время для публикации {selected_date.strftime('%d.%m.%Y')}:", 
                    reply_markup=get_time_keyboard(selected_date)
                )
                return

            if callback.data.startswith('delay_time_'):
                date_str, hour_str = callback.data.split('_')[2:]
                publish_datetime = datetime.fromisoformat(date_str).replace(
                    hour=int(hour_str), minute=0, second=0
                )

                post_id = self.temp_post_data.get('post_id', str(uuid.uuid4().hex[:8]))
                post_data = {
                    'post_id': post_id,
                    'message_id': self.temp_post_data['post_id'],
                    'chat_id': callback.message.chat.id,
                    'scheduled_time': publish_datetime.isoformat(),
                    'city': self.temp_post_data['city'],
                    'approved_by': format_username(callback.from_user),
                    'status': 'delayed'
                }
                self.db.add_post(post_data)

                await callback.message.edit_text(
                    f"⏳ Пост отложен на {publish_datetime.strftime('%H:%M %d.%m.%Y')}\n\n"
                    f"{self.temp_post_data['message']}\n\n"
                    f"👤 Отложил: {format_username(callback.from_user)}\n"
                    f"🆔 ID поста: {post_id}"
                )

            await callback.answer(show_alert=False)
            
        except Exception as e:
            await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
            print(f"Error in process_delay_time: {e}")

    async def handle_custom_time(self, message: types.Message, state: FSMContext):
        try:
            time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
            if not re.match(time_pattern, message.text):
                await message.answer(
                    "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 14:30)\n"
                    "Попробуйте еще раз:"
                )
                return

            hours, minutes = map(int, message.text.split(':'))
            now = datetime.now()
            publish_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            
            if publish_time <= now:
                publish_time += timedelta(days=1)
            post_data = {
                'post_id': str(uuid.uuid4().hex[:8]),
                'message_id': self.temp_post_data['post_id'],
                'chat_id': self.temp_post_data['chat_id'],
                'scheduled_time': publish_time.isoformat(),
                'city': self.temp_post_data['city'],
                'approved_by': self.temp_post_data['approved_by'],
                'status': 'delayed'
            }
            self.db.add_post(post_data)

            # ce accept post v moder group and send message to user about delay || ne lomaite format
            await self.bot.edit_message_text(
                f"⏳ Пост отложен на {publish_time.strftime('%H:%M %d.%m.%Y')}\n\n"
                f"{self.temp_post_data['message']}\n\n"
                f"👤 Отложил: {format_username(message.from_user)}",
                chat_id=self.temp_post_data['chat_id'],
                message_id=message.message_id - 1
            )
            
            await state.clear()

        except ValueError:
            await message.answer(
                "❌ Ошибка при обработке времени. Используйте формат ЧЧ:ММ (например, 14:30)\n"
                "Попробуйте еще раз:"
            )
        except Exception as e:
            await message.answer(f"❌ Произошла ошибка: {str(e)}")
            await state.clear()

    async def schedule_post(self, event, publish_time):
        post_data = {
            'post_id': str(uuid.uuid4().hex[:8]),
            'message_id': self.temp_post_data['post_id'],
            'chat_id': event.message.chat.id,
            'scheduled_time': publish_time.isoformat(),
            'city': self.temp_post_data['city'],
            'approved_by': self.temp_post_data['approved_by'],
            'status': 'delayed'
        }
        self.db.add_post(post_data)

        await event.message.edit_text(
            f"⏳ Пост отложен на {publish_time.strftime('%H:%M %d.%m.%Y')}\n\n"
            f"{self.temp_post_data['message']}\n\n"
            f"👤 Отложил: {format_username(event.from_user)}"
        )
        await event.answer()

        # ce gud
        try:
            username = event.from_user.username or str(event.from_user.id)
            user_id = self.user_state.get_user_id(username)
            if user_id:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"📅 Ваш пост запланирован на {publish_time.strftime('%H:%M %d.%m.%Y')}"
                )
        except Exception as e:
            print(f"Ошибка отправки уведомления о планировании: {e}")

    async def handle_another_post(self, message: types.Message, state: FSMContext):
        await message.answer(
            "🌆 Выберите город для нового поста:",
            reply_markup=get_city_keyboard()
        )
        await state.set_state(PostStates.waiting_for_city)

    async def handle_finish(self, message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "👋 Спасибо за использование бота!\n"
            "Чтобы создать новый пост, нажмите /start",
            reply_markup=get_final_keyboard()
        )

    async def publish_posts(self):
        while True:
            try:
                posts = self.db.get_pending_posts()
                for post in posts:
                    post_id, message_id, chat_id, scheduled_time, city, approved_by, status, content, _ = post
                    try:
                        # Преобразуем message_id в целое число, если это возможно
                        if message_id.isdigit():
                            message_id = int(message_id)
                        else:
                            raise ValueError(f"Invalid message_id: {message_id}")

                        sent_message = await self.bot.copy_message(
                            chat_id=CITIES.get(city, MODERGROUP_ID),
                            from_chat_id=MODERGROUP_ID,
                            message_id=message_id
                        )
                        
                        if sent_message:
                            await self.bot.send_message(
                                MODERGROUP_ID,
                                f"✅ Пост успешно опубликован!\n\n"
                                f"🏙 Город: {city}\n"
                                f"👤 Одобрил: {approved_by}\n"
                                f"🆔 ID поста: {post_id}"
                            )
                            self.db.mark_as_published(post_id)
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Ошибка при публикации поста {post_id}: {error_msg}")
                        await self.bot.send_message(
                            MODERGROUP_ID,
                            f"❌ Ошибка при публикации поста {post_id}:\n{error_msg}"
                        )
                
                if datetime.now().minute % 5 == 0:
                    self.db.clean_old_posts()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Ошибка в publish_posts: {e}")
            
            await asyncio.sleep(30)

    async def cmd_delete(self, message: types.Message):
        if message.chat.id != int(MODERGROUP_ID):
            return

        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM scheduled_posts 
            WHERE is_published = 0 
            ORDER BY scheduled_time ASC
        ''')
        active_posts = cursor.fetchall()

        if not active_posts:
            await message.reply("❌ Нет отложенных постов")
            return

        page = 0
        total_pages = (len(active_posts) + self.posts_per_page - 1) // self.posts_per_page
        start_idx = page * self.posts_per_page
        end_idx = min(start_idx + self.posts_per_page, len(active_posts))

        posts_list = "📋 Отложенные посты:\n\n"
        for i in range(start_idx, end_idx):
            post = active_posts[i]
            post_id, message_id, chat_id, scheduled_time, city, approved_by, status, content, _ = post
            post_time = datetime.fromisoformat(scheduled_time)
            
            posts_list += (
                f"🆔 {post_id}\n"
                f"⏰ {post_time.strftime('%H:%M %d.%m.%Y')}\n"
                f"📍 {city}\n"
                f"📝 {status}\n"
                f"❌ /del_{post_id}\n\n"
            )

        posts_list += f"\nСтраница {page + 1} из {total_pages}"

        await message.reply(
            posts_list,
            reply_markup=get_post_keyboard(page, total_pages)
        )

    async def handle_message(self, message: types.Message):
        if not message.text:
            return
            
        if message.text.startswith('/del_'):
            post_id = message.text[5:].split('@')[0]
            
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM scheduled_posts WHERE id = ?', (post_id,))
            post = cursor.fetchone()
            
            if post:
                post_id, message_id, chat_id, scheduled_time, city, approved_by, status, content, _ = post
                
                if str(message.chat.id) != MODERGROUP_ID:
                    await message.reply("❌ У вас нет прав для удаления постов")
                    return
                
                cursor.execute('DELETE FROM scheduled_posts WHERE id = ?', (post_id,))
                self.db.conn.commit()
                
                post_time = datetime.fromisoformat(scheduled_time)
                await message.reply(
                    f"✅ Пост {post_id} удален\n"
                    f"⏰ Время: {post_time.strftime('%H:%M %d.%m.%Y')}\n"
                    f"🌆 Город: {city}\n"
                    f"👤 Удалил: {format_username(message.from_user)}"
                )
            else:
                await message.reply("❌ Пост не найден")

    async def process_page_navigation(self, callback: types.CallbackQuery):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM scheduled_posts 
            WHERE is_published = 0 
            ORDER BY scheduled_time ASC
        ''')
        active_posts = cursor.fetchall()
        
        page = int(callback.data.split('_')[1])
        total_pages = (len(active_posts) + self.posts_per_page - 1) // self.posts_per_page
        
        if 0 <= page < total_pages:
            start_idx = page * self.posts_per_page
            end_idx = min(start_idx + self.posts_per_page, len(active_posts))
            
            posts_list = "📋 Отложенные посты:\n\n"
            for i in range(start_idx, end_idx):
                post = active_posts[i]
                post_id, message_id, chat_id, scheduled_time, city, approved_by, status, content, _ = post
                post_time = datetime.fromisoformat(scheduled_time)
                
                posts_list += (
                    f"🆔 {post_id}\n"
                    f"⏰ {post_time.strftime('%H:%M %d.%m.%Y')}\n"
                    f"📍 {city}\n"
                    f"📝 {status}\n"
                    f"❌ /del_{post_id}\n\n"
                )

            posts_list += f"\nСтраница {page + 1} из {total_pages}"
            
            await callback.message.edit_text(
                posts_list,
                reply_markup=get_post_keyboard(page, total_pages)
            )

        await callback.answer(show_alert=False)

    async def process_delete_confirmation(self, callback: types.CallbackQuery):
        try:
            post_index = int(callback.data.split('_')[1])
            if 0 <= post_index < len(self.scheduled_posts):
                post = self.scheduled_posts[post_index]
                self.scheduled_posts.pop(post_index)
                self.save_posts()
                
                post_time = datetime.fromisoformat(post['scheduled_time'])
                await callback.message.edit_text(
                    f"✅ Пост удален:\n"
                    f"🕐 Время: {post_time.strftime('%H:%M %d.%m.%Y')}\n"
                    f"🌆 Город: {post['city']}\n"
                    f"👤 Удалил: {format_username(callback.from_user)}"
                )
            else:
                await callback.answer("❌ Пост не найден")
        except (ValueError, IndexError) as e:
            await callback.answer("❌ Ошибка при удалении поста")
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer(show_alert=False)

    async def process_manager_decision(self, callback: CallbackQuery):
        try:
            action, post_id = callback.data.split('_', 1)
            message_text = callback.message.text
            username = None

            # Извлекаем username из сообщения
            for line in message_text.split('\n'):
                if "Пользователь:" in line:
                    username = line.split('Пользователь:')[1].strip()
                    username = username.lstrip('@')
                    break

            if not username:
                raise ValueError("Не удалось определить пользователя")

            manager = format_username(callback.from_user)
            current_time = datetime.now().strftime('%H:%M %d.%m.%Y')
            
            is_approved = action == 'approve'
            status = "✅ Одобрено" if is_approved else "❌ Отклонено"

            # Обновляем сообщение в группе модерации
            await callback.message.edit_text(
                f"{message_text}\n\n"
                f"{status} модератором {manager}\n"
                f"⏰ {current_time}",
                reply_markup=None
            )

            try:
                # Получаем user_id из UserState
                user_id = self.user_state.get_user_id(username)
                if user_id:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"Статус вашего поста изменен: {status}"
                    )
                else:
                    print(f"Не удалось найти user_id для username: {username}")
            except Exception as e:
                print(f"Ошибка при отправке уведомления пользователю {username}: {e}")
                
        except Exception as e:
            print(f"Ошибка обработки решения модератора: {e}")
            await callback.answer(
                "Произошла ошибка при обработке решения",
                show_alert=True
            )

    async def start(self):
        asyncio.create_task(self.publish_posts())
        await self.dp.start_polling(self.bot)

    async def stop(self):
        self.db.close()

async def main():
    post_bot = PostBot(TOKEN)
    await post_bot.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:        pass