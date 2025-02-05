# ce uslugi blya
from asyncio.log import logger
from datetime import datetime
from aiogram import Bot, Dispatcher, Router
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
                          ReplyKeyboardMarkup, KeyboardButton)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
from aiogram.types import Message
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.default import DefaultBotProperties
import aiohttp

API_TOKEN = "7802098774:AAG9Jec3E5v_Hk8Fg3F-pTalxMJZ-wAteXk"
CRYPTOBOT_TOKEN = "332687:AA3xGRAM6IJGHmFj3ZEAIz570WsOjBfG567"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"
MANAGERS_GROUP_ID = "-1002423702325"
BINANCE_ID = "756008063"
BYBIT_ID = "310554555"
CRYPTOBOT_USERNAME = "@CryptoBot"

ADMIN_USERNAME = "@iminternethero" # na vsyakiy sluchay

SERVICE_PRICES = {
    "unban": 250,
    "fast_post": 100,
    "delete_post": 300,
    "find_sender": 200,
    "moderator_rights": 1000,
    "reserve": 500
}

SERVICE_NAMES = {
    "unban": "Разбан 🙏",
    "fast_post": "Пост без очереди 📥",
    "delete_post": "Удаление поста 🗑",
    "find_sender": "Узнать кто отправил пост 👀",
    "moderator_rights": "Права модератора чата 👑",
    "reserve": "Бронь 🛡"
}

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

class OrderProcess(StatesGroup):
    username = State()
    service = State()
    payment_method = State()
    chat_selection = State()
    post_content = State()
    post_media = State()
    post_preview = State()
    post_link = State()
    payment_screenshot = State()
    moderator_info = State()

class SenderInfoState(StatesGroup):
    waiting_for_info = State()
    confirming_info = State()

usernames = {}

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Все категории")],
            [KeyboardButton(text="👤 Изменить профиль")],
            [KeyboardButton(text="🛠 Поддержка")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard

PAYMENT_INFO = {
    "Binance": {"name": "Binance", "id": BINANCE_ID},
    "ByBit": {"name": "ByBit", "id": BYBIT_ID},
    "CryptoBot": {"name": "CryptoBot"},
    "FunPay": {"name": "FunPay"}
}

FUNPAY_LINKS = {
    "moderator_rights": "https://funpay.com/lots/offer?id=37537259",
    "reserve": "https://funpay.com/lots/offer?id=37537032",
    "fast_post": "https://funpay.com/lots/offer?id=37536907",
    "find_sender": "https://funpay.com/lots/offer?id=37536858",
    "delete_post": "https://funpay.com/lots/offer?id=37536800",
    "unban": "https://funpay.com/lots/offer?id=37536658"
}

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Binance", callback_data="Binance")],
        [InlineKeyboardButton(text="ByBit", callback_data="ByBit")],
        [InlineKeyboardButton(text="CryptoBot", callback_data="CryptoBot")],
        [InlineKeyboardButton(text="FunPay", callback_data="FunPay")]
    ])

def get_chat_list_markup():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пермь", callback_data="chat_1")],
        [InlineKeyboardButton(text="Владивосток", callback_data="chat_2")],
        [InlineKeyboardButton(text="Казань", callback_data="chat_3")],
        [InlineKeyboardButton(text="Краснодар", callback_data="chat_4")],
        [InlineKeyboardButton(text="Саратов", callback_data="chat_5")]
    ])

def service_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разбан 🙏", callback_data="unban")],
        [InlineKeyboardButton(text="Пост без очереди 📥", callback_data="fast_post")],
        [InlineKeyboardButton(text="Удаление поста 🗑", callback_data="delete_post")],
        [InlineKeyboardButton(text="Узнать кто отправил пост 👀", callback_data="find_sender")],
        [InlineKeyboardButton(text="Права модератора чата 👑", callback_data="moderator_rights")],
        [InlineKeyboardButton(text="Бронь 🛡", callback_data="reserve")]
    ])

def get_start_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать новую услугу")]],
        resize_keyboard=True,
        is_persistent=True
    )
    return keyboard

@router.message(lambda message: message.text == "Отменить услугу")
async def cancel_service(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if not current_state or current_state == OrderProcess.username:
        await message.answer(
            "❌ Нечего отменять. Сначала выберите услугу.",
            reply_markup=service_keyboard()
        )
        return
    
    await state.clear()
    await message.answer(
        "Заявка отменена ❌\n"
        "Выберите новую услугу:",
        reply_markup=service_keyboard()
    )
    await state.set_state(OrderProcess.service)

@router.message(lambda message: message.text == "Начать новую услугу")
async def start_new_service(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == OrderProcess.username:
        return
    
    if not current_state or current_state == OrderProcess.service:
        return
    
    data = await state.get_data()
    username = data.get('username')
    
    if not username:
        await message.answer(
            "❌ Ошибка: данные пользователя не найдены.\n"
            "Пожалуйста, начните заново с команды /start"
        )
        await state.clear()
        await state.set_state(OrderProcess.username)
        return
    
    await state.clear()
    await state.update_data(username=username)
    await message.answer(
        f"✅ Выберите новую услугу\n"
        f"Username для связи: @{username}",
        reply_markup=service_keyboard()
    )
    await state.set_state(OrderProcess.service)

@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    if message.chat.type != 'private':
        return
        
    user_id = message.from_user.id
    username = usernames.get(user_id)
    
    if username:
        await message.answer(
            f"Привет!👋\n\n"
            f"Ваш текущий username: @{username}\n\n"
            "Нажмите 🎯 Все категории для выбора услуги или 👤 Изменить профиль для изменения username.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "Привет!👋\n\n"
            "⚠️ ВНИМАНИЕ! Укажите свой Telegram username (без @).\n"
            "Это важно, так как username будет использоваться для связи с вами.\n\n"
            "❌ Неправильно: @username, https://t.me/username\n"
            "✅ Правильно: username",
            link_preview_options={"is_disabled": True},
            reply_markup=get_main_keyboard()
        )
        await state.set_state(OrderProcess.username)

@router.message(lambda message: message.text == "🎯 Все категории")
async def show_categories(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = usernames.get(user_id)
    
    if not username:
        await message.answer(
            "❌ Для доступа к услугам необходимо указать username.\n"
            "Пожалуйста, нажмите кнопку 👤 Изменить профиль"
        )
        return
    
    await message.answer(
        f"Выберите услугу:\n"
        f"Текущий профиль: @{username}",
        reply_markup=service_keyboard()
    )
    await state.set_state(OrderProcess.service)

@router.message(lambda message: message.text == "👤 Изменить профиль")
async def change_profile(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ ВНИМАНИЕ! Укажите свой Telegram username (без @).\n"
        "Это важно, так как username будет использоваться для связи с вами.\n\n"
        "❌ Неправильно: @username, https://t.me/username\n"
        "✅ Правильно: username",
        link_preview_options={"is_disabled": True}
    )
    await state.set_state(OrderProcess.username)

@router.message(lambda message: message.text == "🛠 Поддержка")
async def support(message: Message):
    await message.answer(
        "🛠 Если вам нужна помощь или у вас возникли вопросы, не стесняйтесь обратиться за поддержкой!\n\n"
        "💬 Напишите нам сюда: @zerkalosupportbot\n\n"
        "📩 Мы готовы помочь вам с любыми вопросами или предоставить дополнительную информацию."
    )
 
BLACKLIST_WORDS = [
    "sa1tem", "start"
]

def validate_username(username: str) -> tuple[bool, str]:
    username = username.lower().strip()
    
    if not username:
        return False, "Username не может быть пустым"
    
    if username.startswith('@'):
        username = username[1:]
    
    if ' ' in username or not all(c.isalnum() or c == '_' for c in username):
        return False, "Username может содержать только буквы, цифры и _ (подчеркивание)"
    
    if len(username) < 5:
        return False, "Username должен содержать минимум 5 символов"
        
    if len(username) > 32:
        return False, "Username не должен превышать 32 символа"
    
    blacklist_words = [
        "начать", "новую", "услугу", "start"
    ]
    
    for word in blacklist_words:
        if word in username:
            return False, f"Username не может содержать слово: {word}"
    
    if username[0].isdigit():
        return False, "Username не может начинаться с цифры"
    
    if not all(c.isascii() for c in username):
        return False, "Username может содержать только английские буквы"
    
    return True, username

@router.message(OrderProcess.username)
async def get_username(message: Message, state: FSMContext):
    username = message.text.strip()
    is_valid, result = validate_username(username)
    
    if not is_valid:
        await message.answer(
            f"❌ Ошибка: {result}\n"
            "Укажите корректный username."
        )
        return
    
    user_id = message.from_user.id
    usernames[user_id] = result
    
    await state.update_data(username=result)
    await message.answer(
        f"✅ Профиль обновлен\n"
        f"Ваш username: @{result}\n\n"
        "Нажмите 🎯 Все категории для выбора услуги",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data.in_(["unban", "fast_post", "delete_post", "find_sender", "moderator_rights", "reserve"]))
async def handle_service_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    username = usernames.get(user_id)
    
    if not username:
        await callback.message.answer(
            "❌ Для выбора услуги необходимо указать username.\n"
            "Пожалуйста, нажмите кнопку 👤 Изменить профиль"
        )
        return
    
    service = callback.data
    amount = SERVICE_PRICES[service]
    
    await state.update_data(
        service=SERVICE_NAMES[service],
        amount=amount,
        username=username
    )
    
    service_message = (
        f"Выбрана услуга: {SERVICE_NAMES[service]}\n"
        f"Стоимость: {amount} рублей\n"
        f"Username для связи: @{username}\n\n"
    )
    
    if service == "find_sender":
        await callback.message.answer(
            service_message +
            "⚠️ Сначала администратор проверит наличие данных.\n"
            "Пожалуйста, отправьте ссылку на пост:"
        )
        await state.set_state(OrderProcess.post_link)
    elif service == "delete_post":
        await callback.message.answer(
            service_message +
            "Пожалуйста, отправьте ссылку на пост, который нужно удалить:"
        )
        await state.set_state(OrderProcess.post_link)
    elif service == "reserve":
        await callback.message.answer(
            service_message +
            "Для оформления брони, пожалуйста, выберите способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderProcess.payment_method)
    elif service == "moderator_rights":
        await callback.message.answer(
            service_message +
            "Для получения прав модератора, пожалуйста, выберите чат:",
            reply_markup=get_chat_list_markup()
        )
        await state.set_state(OrderProcess.chat_selection)
    elif service == "fast_post":
        await callback.message.answer(
            service_message +
            "Выберите чат, в который нужно опубликовать пост:",
            reply_markup=get_chat_list_markup()
        )
        await state.set_state(OrderProcess.chat_selection)
    else:
        if service == "unban":
            await callback.message.answer(
                service_message +
                "Выберите чат для разбана:",
                reply_markup=get_chat_list_markup()
            )
            await state.set_state(OrderProcess.chat_selection)
        else:
            await callback.message.answer(
                service_message +
                "Нажмите кнопку для оплаты:",
                reply_markup=payment_keyboard()
            )
            await state.set_state(OrderProcess.payment_method)

@router.message(OrderProcess.post_link)
async def handle_post_link(message: Message, state: FSMContext):
    link = message.text.strip()
    data = await state.get_data()
    service = data.get('service')
    
    if not link:
        await message.answer("❌ Ошибка: отправьте корректную ссылку")
        return
    
    await state.update_data(post_link=link)
    
    if service == SERVICE_NAMES["find_sender"]:
        amount = SERVICE_PRICES["find_sender"]
        await message.answer(
            f"Стоимость услуги: {amount} рублей\n"
            "Выберите способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderProcess.payment_method)
    else:
        await message.answer(
            "Ссылка получена.\n"
            "Выберите способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderProcess.payment_method)

@router.callback_query(F.data.startswith("chat_"))
async def handle_chat_selection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    chat_name = {
        "chat_1": "Пермь",
        "chat_2": "Владивосток",
        "chat_3": "Казань",
        "chat_4": "Краснодар",
        "chat_5": "Саратов"
    }.get(callback.data)
    
    data = await state.get_data()
    service = data.get('service')
    await state.update_data(chat_name=chat_name)

    if service == SERVICE_NAMES["fast_post"]:
        await callback.message.answer(
            f"Выбран чат: {chat_name}\n"
            "📝 Отправьте ваш пост (текст, фото или видео):"
        )
        await state.set_state(OrderProcess.post_content)
    elif service == SERVICE_NAMES["moderator_rights"]:
        await callback.message.answer(
            f"Выбран чат: {chat_name}\n"
            "Выберите способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderProcess.payment_method)
    else:
        await callback.message.answer(
            f"Выбран чат: {chat_name}\n"
            "Выберите способ оплаты:",
            reply_markup=payment_keyboard()
        )
        await state.set_state(OrderProcess.payment_method)

class PostContent:
    def __init__(self):
        self.text = ""
        self.media = []

post_contents = {}

@router.message(OrderProcess.post_content)
async def handle_post_content(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in post_contents:
        post_contents[user_id] = PostContent()
    
    content = post_contents[user_id]
    
    if message.text:
        content.text = message.text
    
    if message.photo:
        content.media.append({
            'type': 'photo',
            'file_id': message.photo[-1].file_id
        })
    
    if message.video:
        content.media.append({
            'type': 'video',
            'file_id': message.video.file_id
        })
    
    preview_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Предпросмотр", callback_data="preview_post")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="finish_post")],
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart_post")]
    ])
    
    await message.answer(
        "Контент добавлен. Выберите действие:",
        reply_markup=preview_keyboard
    )

@router.callback_query(F.data == "preview_post")
async def show_post_preview(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    content = post_contents.get(user_id)
    
    if not content:
        await callback.message.answer("Ошибка: контент не найден")
        return
    
    if content.text:
        await callback.message.answer(f"Текст поста:\n\n{content.text}")
    
    for media in content.media:
        if media['type'] == 'photo':
            await callback.message.answer_photo(media['file_id'])
        elif media['type'] == 'video':
            await callback.message.answer_video(media['file_id'])
    
    await callback.message.answer(
        "Проверьте контент поста.\n"
        "Если нужно изменить - нажмите 'Начать заново'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Все верно", callback_data="finish_post")],
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart_post")]
        ])
    )

@router.callback_query(F.data == "restart_post")
async def restart_post(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id in post_contents:
        del post_contents[user_id]
    
    await callback.message.answer(
        "Отправьте новый контент для поста (текст, фото, видео).\n"
        "Можно отправить несколько файлов подряд:"
    )
    await state.set_state(OrderProcess.post_content)
@router.callback_query(F.data == "finish_post")
async def finish_post(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    content = post_contents.get(user_id)
    
    if not content:
        await callback.message.answer("Ошибка: контент не найден")
        return
    
    await state.update_data(
        post_content=content.text,
        post_media=content.media
    )
    
    await callback.message.answer(
        "Контент поста сохранен.\n"
        "Выберите способ оплаты:",
        reply_markup=payment_keyboard()
    )
    await state.set_state(OrderProcess.payment_method)

async def send_order_to_managers(data: dict):
    current_time = datetime.now().strftime('%H:%M %d.%m.%Y')
    payment_method = data.get('payment_method', 'Не указан')
    service = data.get('service')
    
    try:
        screenshot_msg = None
        if 'screenshot_id' in data:
            screenshot_msg = await bot.send_photo(
                chat_id=MANAGERS_GROUP_ID,
                photo=data['screenshot_id'],
                caption="💳 Скриншот оплаты"
            )

        message_text = (
            f"💫 Новая заявка!\n\n"
            f"👤 Пользователь: @{data['username']}\n"
            f"💎 Услуга: {data['service']}\n"
            f"💰 Сумма: {data['amount']} рублей\n"
            f"💳 Способ оплаты: {payment_method}\n"
        )

        if 'payment_info' in data:
            message_text += f"📝 {data['payment_info']}\n"
            
        if 'post_content' in data:
            message_text += f"📝 Текст поста: {data['post_content']}\n"
        if 'post_link' in data:
            message_text += f"🔗 Ссылка на пост: {data['post_link']}\n"
        if 'chat_name' in data:
            message_text += f"📍 Чат: {data['chat_name']}\n"
            
        message_text += f"⏰ Время: {current_time}"
        
        if service == SERVICE_NAMES["find_sender"]:
            verification_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Информация найдена", 
                                       callback_data=f"data_available_{data['username']}"),
                    InlineKeyboardButton(text="❌ Информация не найдена", 
                                       callback_data=f"no_data_{data['username']}")
                ]
            ])
            await bot.send_message(
                chat_id=MANAGERS_GROUP_ID,
                text=message_text,
                reply_markup=verification_keyboard,
                reply_to_message_id=screenshot_msg.message_id if screenshot_msg else None
            )
        else:
            msg = await bot.send_message(
                chat_id=MANAGERS_GROUP_ID,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{data['username']}"),
                        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{data['username']}")
                    ]
                ]),
                reply_to_message_id=screenshot_msg.message_id if screenshot_msg else None
            )

        if 'post_media' in data and screenshot_msg:
            for media in data['post_media']:
                if media['type'] == 'photo':
                    await bot.send_photo(
                        chat_id=MANAGERS_GROUP_ID,
                        photo=media['file_id'],
                        caption="📎 Медиафайл для поста",
                        reply_to_message_id=screenshot_msg.message_id
                    )
                elif media['type'] == 'video':
                    await bot.send_video(
                        chat_id=MANAGERS_GROUP_ID,
                        video=media['file_id'],
                        caption="📎 Медиафайл для поста",
                        reply_to_message_id=screenshot_msg.message_id
                    )
    except Exception as e:
        logger.error(f"Error sending order to managers: {e}")
        raise

@router.callback_query(lambda c: c.data.startswith(("data_available_", "no_data_")))
async def handle_data_verification(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        action, username = callback.data.rsplit("_", 1)
        is_available = action == "data_available"
        manager = callback.from_user.username
        current_time = datetime.now().strftime('%H:%M %d.%m.%Y')
        
        if is_available:
            await state.update_data(target_username=username)
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"✅ Информация найдена\n"
                f"Проверил: @{manager}\n"
                f"⏰ {current_time}"
            )
            await callback.message.answer(
                "Введите информацию об отправителе поста:"
            )
            await state.set_state(SenderInfoState.waiting_for_info)
            
            user_id = None
            for uid, stored_username in usernames.items():
                if stored_username == username:
                    user_id = uid
                    break
            
            if user_id:
                await bot.send_message(
                    chat_id=user_id,
                    text="✅ Информация найдена и будет отправлена вам после проверки менеджером"
                )
        else:
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"❌ Информация не найдена\n"
                f"Проверил: @{manager}\n"
                f"⏰ {current_time}"
            )
            
            user_id = None
            for uid, stored_username in usernames.items():
                if stored_username == username:
                    user_id = uid
                    break
            
            if user_id:
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ К сожалению, информация об отправителе не найдена"
                )
            
    except Exception as e:
        logger.error(f"Data verification error: {e}")
        await callback.message.answer(
            "Ошибка при обработке. Попробуйте снова."
        )

@router.message(SenderInfoState.waiting_for_info)
async def handle_sender_info(message: Message, state: FSMContext):
    data = await state.get_data()
    target_username = data.get('target_username')
    
    preview_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_sender_info")],
        [InlineKeyboardButton(text="🔄 Изменить", callback_data="edit_sender_info")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data="reject_sender_info")]
    ])
    
    await state.update_data(sender_info=message.text)
    
    await message.answer(
        f"Предпросмотр информации об отправителе:\n\n"
        f"{message.text}\n\n"
        f"Выберите действие:",
        reply_markup=preview_keyboard
    )
    await state.set_state(SenderInfoState.confirming_info)

@router.callback_query(lambda c: c.data in ["confirm_sender_info", "edit_sender_info", "reject_sender_info"])
async def handle_sender_info_action(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    action = callback.data
    data = await state.get_data()
    target_username = data.get('target_username')
    sender_info = data.get('sender_info')

    if action == "confirm_sender_info":
        user_id = None
        for uid, stored_username in usernames.items():
            if stored_username == target_username:
                user_id = uid
                break
                
        if user_id:
            await state.update_data(verified_sender_info=sender_info)
            
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Информация об отправителе поста:\n\n"
                    f"{sender_info}"
                )
            )
            
            await callback.message.edit_text(
                f"{callback.message.text}\n"
                "✅ Информация отправлена пользователю"
            )
        else:
            await callback.message.answer("❌ Ошибка: пользователь не найден")
            
    elif action == "edit_sender_info":
        await callback.message.answer("Введите новую информацию об отправителе:")
        await state.set_state(SenderInfoState.waiting_for_info)
    
    elif action == "reject_sender_info":
        await callback.message.edit_text("❌ Информация отклонена")
        await state.finish()

@router.callback_query(lambda c: c.data.startswith(("approve_", "decline_")))
async def handle_manager_decision(callback: CallbackQuery):
    await callback.answer()
    try:
        action, username = callback.data.split("_")
        manager = callback.from_user.username
        current_time = datetime.now().strftime('%H:%M %d.%m.%Y')
        
        message_text = callback.message.text
        service_name = None
        for line in message_text.split('\n'):
            if "Услуга:" in line:
                service_name = line.split("Услуга:")[1].strip()
                break

        is_approved = action == "approve"
        status = "✅ Подтверждено" if is_approved else "❌ Отклонено"
        
        try:
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"{status} менеджером @{manager}\n"
                f"⏰ {current_time}",
                reply_markup=None,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
        
        await update_order_status(username, status)
        
        try:
            users = await db_get_user_info(username)
            if users and users.get('user_id'):
                user_id = users['user_id']
                if is_approved:
                    if service_name == SERVICE_NAMES["find_sender"]:
                        sender_info = await get_sender_info_for_user(username)
                        if sender_info:
                            await bot.send_message(
                                chat_id=user_id,
                                text=(
                                    "✅ Оплата подтверждена!\n"
                                    "Информация об отправителе поста:\n\n"
                                    f"{sender_info}"
                                )
                            )
                        else:
                            await bot.send_message(
                                chat_id=user_id,
                                text="❌ Ошибка: информация об отправителе не найдена"
                            )
                    else:
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"✅ Ваша заявка на услугу '{service_name}' одобрена и будет выполнена!"
                        )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Ваша заявка на услугу '{service_name}' отклонена"
                    )
            else:
                logger.warning(f"Не удалось найти user_id для username: {username}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {username}: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки решения менеджера: {e}")
        await callback.answer(
            "Произошла ошибка при обработке решения",
            show_alert=True
        )

async def get_sender_info_for_user(username: str) -> str:
    sender_info_storage = {}
    return sender_info_storage.get(username)

order_statuses = {}

async def update_order_status(username: str, new_status: str):
    order_statuses[username] = new_status

async def db_get_user_info(username: str) -> dict:
    for user_id, stored_username in usernames.items():
        if stored_username == username:
            return {"user_id": user_id, "username": username}
    return None

async def create_cryptobot_invoice(amount: int, description: str) -> str:
    async with aiohttp.ClientSession() as session:
        payload = {
            "asset": "USDT",
            "amount": str(amount / 100),
            "description": description,
            "payload": f"invoice_{amount}_{int(datetime.now().timestamp())}"
        }
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        
        async with session.post(
            f"{CRYPTOBOT_API_URL}/createInvoice",
            json=payload,
            headers=headers
        ) as response:
            result = await response.json()
            if result.get("ok"):
                return result["result"]["pay_url"]
            raise Exception(f"Ошибка создания инвойса: {result}")

@router.callback_query(F.data.in_(PAYMENT_INFO.keys()))
async def payment_method(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    payment_method = callback.data
    payment_info = PAYMENT_INFO[payment_method]
    data = await state.get_data()
    
    try:
        amount = data.get('amount', 0)
        service = data.get('service', 'Услуга')
        
        await state.update_data(payment_method=payment_method)
        
        if payment_method == "FunPay":
            service_key = next((k for k, v in SERVICE_NAMES.items() if v == service), None)
            funpay_link = FUNPAY_LINKS.get(service_key, '')
            await callback.message.answer(f"🔗 Ссылка на оплату: {funpay_link}")
            await state.clear()
            return
            
        elif payment_method == "CryptoBot":
            try:
                payment_url = await create_cryptobot_invoice(
                    amount=amount,
                    description=f"Оплата услуги: {service}"
                )
                
                await callback.message.answer(
                    f"💳 Способ оплаты: {payment_info['name']}\n"
                    f"💰 Сумма к оплате: {amount} RUB ≈ {amount/100} USDT\n\n"
                    "1️⃣ Нажмите кнопку «Оплатить» ниже\n"
                    "2️⃣ Выберите удобную криптовалюту для оплаты\n"
                    "3️⃣ После оплаты вернитесь сюда\n"
                    "4️⃣ Нажмите кнопку «Я оплатил»\n\n",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"💳 Оплатить {amount} RUB", url=payment_url)],
                        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="confirm_payment")]
                    ])
                )
            except Exception as e:
                logger.error(f"CryptoBot payment error: {e}")
                await callback.message.answer("Ошибка создания платежа. Попробуйте другой способ оплаты.")
        else:
            user_id = payment_info["id"]
            await callback.message.answer(
                f"💳 Способ оплаты: {payment_info['name']}\n"
                f"💰 Сумма: {amount} RUB ≈ {amount/100} USDT\n"
                f"ID пользователя: {user_id}\n\n"
                f"Пожалуйста, отправьте TX ID транзакции:"
            )
            await state.set_state(OrderProcess.payment_screenshot)
            
    except Exception as e:
        logger.error(f"Payment method error: {e}")
        await callback.message.answer("❌ Произошла ошибка. Попробуйте другой способ оплаты.")

@router.callback_query(F.data == "confirm_payment")
async def handle_payment_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payment_method = data.get('payment_method')
    
    if payment_method in ["CryptoBot", "FunPay"]:
        await process_payment(callback.message, data, state)
    else:
        await callback.message.answer("❌ Сначала отправьте TX ID транзакции")

async def process_payment(message: Message, data: dict, state: FSMContext):
    """Process payment and send order to managers"""
    try:
        username = data['username']
        await update_order_status(username, "На проверке")
        
        await send_order_to_managers(data)
        
        await message.answer(
            "✅ Заявка отправлена на проверку\n"
            f"Текущий статус: {order_statuses.get(username, 'На проверке')}"
        )
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке заявки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
    finally:
        await state.clear()

@router.message(OrderProcess.payment_screenshot)
async def handle_payment_screenshot(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer(
                "❌ Отправьте TX ID транзакции (ID транзакции)"
            )
            return
            
        data = await state.get_data()
        tx_id = message.text.strip()
        data['tx_id'] = tx_id
        
        payment_method = data.get('payment_method', '')
        if payment_method in ["Binance", "ByBit"]:
            data['payment_info'] = f"TX ID: {tx_id}"
        
        await process_payment(message, data, state)
        
    except Exception as e:
        logger.error(f"Payment TX ID error: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке TX ID.\n"
            "Пожалуйста, попробуйте отправить TX ID еще раз."
        )

dp.include_router(router)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(
            command="start",
            description="Перезапустить бота"
        )
    ]
    
    await bot.set_my_commands(commands, BotCommandScopeDefault())

async def main():
    try:
        await set_commands(bot)
        await dp.start_polling(bot)
    except Exception as e:
        await bot.send_message(MANAGERS_GROUP_ID, f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        asyncio.run(bot.send_message(MANAGERS_GROUP_ID, "Бот остановлен"))
    except Exception as e:
        asyncio.run(bot.send_message(MANAGERS_GROUP_ID, f"Критическая ошибка: {e}"))