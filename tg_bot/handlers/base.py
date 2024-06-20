import uuid

from dotenv import load_dotenv
from os import getenv

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, get_user_ids, get_roles
from utils.backend_methods import get_law_update
from handlers.states import BotStates

load_dotenv(dotenv_path="../tg_conf.env")

AUTH_URL = getenv('AUTH_URL')

base_router = Router()


@base_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if get_token(message.from_user.id):
        user_roles = get_roles(message.from_user.id)
        if user_roles and "tg_admin" in user_roles:
            await state.set_state(BotStates.admin_choosing_action)
            admin_greet = await message.answer("<b>Добро пожаловать в Админ-панель бота для автоматизации покупок!</b>\n\nПожалуйста, выберите одно из предложенных ниже действий.", parse_mode="html",
                                             reply_markup=keyboard_builder(["Загрузить складские остатки",
                                                                            "Загрузить обороты по счету"]))
            await state.update_data(admin_greet=admin_greet)
        else:
            await state.set_state(BotStates.choosing_action)
            start_no_auth = await message.answer("<b>Добро пожаловать в бота для автоматизации покупок!</b>\n\nПожалуйста, "
                                                 "выберите одно из предложенных ниже действий или опишите, что Вы хотите "
                                                 "сделать сообщением.", parse_mode="html",
                                                 reply_markup=keyboard_builder(["Узнать складские остатки",
                                                                                "Сформировать прогноз"]))
            await state.update_data(no_auth_greet=start_no_auth)
    else:
        auth_state = str(uuid.uuid4())
        store_session(message.from_user.id, auth_state)
        await state.set_state(BotStates.checking_auth)
        start_message = await message.answer(f"<b>Добро пожаловать в бота для автоматизации покупок!</b>\n\n<a href='"
                             f"{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, для того чтобы "
                             f"продолжить работу в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>",
                             parse_mode="html", reply_markup=keyboard_builder(["Я авторизовался ✅"]))
        await state.update_data(start_greet=start_message)


async def send_news(bot_instance):
    id_list = get_user_ids()
    news_articles = get_law_update()
    if news_articles:
        for user_id in id_list:
            try:
                await bot_instance.send_message(user_id, news_articles)
            except Exception as e:
                print(e)
