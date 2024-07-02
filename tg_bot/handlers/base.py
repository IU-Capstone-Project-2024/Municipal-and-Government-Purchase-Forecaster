import os
import uuid
from dotenv import load_dotenv

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, get_user_ids, get_roles, delete_token
from utils.backend_methods import get_law_update, get_stock_aware
from handlers.states import BotStates

load_dotenv("./tg_conf.env")
AUTH_URL = os.getenv('AUTH_URL')

base_router = Router()


@base_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if get_token(message.from_user.id):
        user_roles = get_roles(message.from_user.id)
        if user_roles and "tg_admin" in user_roles:
            await state.set_state(BotStates.admin_choosing_action)
            admin_greet = await message.answer(
                "<b>Добро пожаловать в Админ-панель бота для автоматизации покупок!</b>\n\nПожалуйста, выберите "
                "одно из предложенных ниже действий.", parse_mode="html",
                reply_markup=keyboard_builder(["Загрузить складские остатки", "Загрузить обороты по счету"]))
            await state.update_data(admin_greet=admin_greet)
        else:
            await state.set_state(BotStates.choosing_action)
            start_no_auth = await message.answer(
                "<b>Добро пожаловать в бота для автоматизации покупок!</b>\n\nПожалуйста, выберите одно из "
                "предложенных ниже действий или опишите, что Вы хотите сделать сообщением.", parse_mode="html",
                reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                               "Отслеживать товары"]))
            await state.update_data(no_auth_greet=start_no_auth)
    else:
        auth_state = str(uuid.uuid4())
        store_session(message.from_user.id, auth_state)
        await state.set_state(BotStates.checking_auth)
        start_message = await message.answer(
            f"<b>Добро пожаловать в бота для автоматизации покупок!</b>\n\n<a href='{AUTH_URL + auth_state}'>"
            "Перейдите по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После авторизации "
            "нажмите кнопку ниже.</b>", parse_mode="html", reply_markup=keyboard_builder(["Я авторизовался ✅"]))
        await state.update_data(start_greet=start_message)


@base_router.message(Command('logout'))
async def logout(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if get_token(user_id):
        delete_token(user_id)
        await state.set_state(BotStates.authing_again)
        start_message = await message.answer("Вы успешно вышли из учетной записи!",
                                             reply_markup=keyboard_builder(["Авторизоваться заново🔄"]))
    else:
        auth_state = str(uuid.uuid4())
        await state.set_state(BotStates.checking_auth)
        store_session(message.from_user.id, auth_state)
        start_message = await message.answer(
            f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, "
            "для того чтобы продолжить работу в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>",
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


async def remain_aware(bot_instance):
    id_list = get_user_ids()
    for user_id in id_list:
        awares_list = get_stock_aware(user_id)
        if awares_list:
            for aware in awares_list:
                try:
                    await bot_instance.send_message(user_id, aware)
                except Exception as e:
                    print(e)

