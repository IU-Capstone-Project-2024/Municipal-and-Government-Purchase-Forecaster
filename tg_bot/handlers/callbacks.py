import json
import math
import os
import time
import uuid
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime
from dateutil.relativedelta import relativedelta

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, is_refresh_expired, delete_token, \
    is_token_expired, refresh_token, get_roles
from handlers.states import BotStates
from utils.backend_methods import get_remains, get_prediction, get_json, delete_track_product, get_users_tracks, \
    add_track_product

# Load environment variables
load_dotenv("./tg_conf.env")
AUTH_URL = os.getenv('AUTH_URL')

# Initialize router
callback_router = Router()

# Define JSON fields and paths for easier access
JSON_FIELDS = ['Идентификатор расчета', 'Идентификатор лота', 'Идентификатор заказчика', 'Дата начала поставки',
               'Дата окончания поставки', 'Объем поставки', 'Год', 'Идентификатор ГАР адреса',
               'Адрес в текстовой форме', 'Сквозной идентификатор СПГЗ', 'Идентификатор СПГЗ',
               'Сумма спецификации', 'Ед. измерения по ОКЕИ', 'Объем поставки']

JSON_PATHS = ['id', 'lotEntityId', 'CustomerId', 'DeliverySchedule.dates.start_date', 'DeliverySchedule.dates.end_date',
              'DeliverySchedule.deliveryAmount', 'DeliverySchedule.year', 'address.gar_id', 'address.text', 'entityId',
              'id', 'nmc', 'okei_code', 'purchaseAmount']


def auth_check(func):
    """Decorator to check user authentication before executing a callback"""
    @wraps(func)
    async def wrapper(query: CallbackQuery, state: FSMContext, *args, **kwargs):
        user_id = query.from_user.id
        if is_refresh_expired(user_id):
            # If refresh token is expired, delete token and request re-authentication
            delete_token(user_id)
            auth_state = str(uuid.uuid4())
            store_session(user_id, auth_state)
            await state.set_state(BotStates.checking_auth)
            await query.message.answer(
                f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                f"авторизации нажмите кнопку ниже.</b>", parse_mode="html")
            return
        else:
            if is_token_expired(user_id):
                # If access token is expired, refresh it
                refresh_token(user_id)
            return await func(query, state, *args, **kwargs)

    return wrapper


@callback_router.callback_query(BotStates.checking_auth)
async def check_authorization(query: CallbackQuery, state: FSMContext):
    """Handler to check user authentication at start"""
    if get_token(query.from_user.id):
        user_roles = get_roles(query.from_user.id)
        if user_roles and "tg_admin" in user_roles:
            # If user is an admin, show admin panel
            await query.message.delete()
            await state.set_state(BotStates.admin_choosing_action)
            admin_greet_message = await query.message.answer(
                "<b>Добро пожаловать в Админ-панель бота для автоматизации покупок!</b>\n\nПожалуйста, выберите одно "
                "из предложенных ниже действий.", parse_mode="html",
                reply_markup=keyboard_builder(["Загрузить складские остатки",
                                               "Загрузить обороты по счету"]))
            await state.update_data(admin_greet=admin_greet_message)
        else:
            # If user is not an admin, show regular user panel
            await query.message.delete()
            await state.set_state(BotStates.choosing_action)
            ask_message = await query.message.answer(
                "<b>Вы успешно авторизовались в боте!</b>✅\n\nПожалуйста, выберите одно из предложенных ниже действий "
                "или опишите, что Вы хотите сделать сообщением.", parse_mode="HTML",
                reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                               "Отслеживать товары"]))
            await state.update_data(start_greet=ask_message)
    else:
        # If user is not authorized, provide authorization link
        await query.message.delete()
        auth_state = str(uuid.uuid4())
        store_session(query.from_user.id, auth_state)
        no_auth_message = await query.message.answer(
            f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите"
            " по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
            f"авторизации нажмите кнопку ниже.</b>", parse_mode="html",
            reply_markup=keyboard_builder(["Я авторизовался ✅"]))
        await state.update_data(start_greet=no_auth_message)


@callback_router.callback_query(BotStates.authing_again)
async def auth_again(query: CallbackQuery, state: FSMContext):
    """Handle re-authorization callback"""
    user_data = await state.get_data()
    await user_data['start_greet'].delete_reply_markup()
    auth_state = str(uuid.uuid4())
    store_session(query.from_user.id, auth_state)
    await state.set_state(BotStates.checking_auth)
    start_message = await query.message.answer(
        f"<a href='{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, для того чтобы продолжить работу "
        "в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>", parse_mode="html",
        reply_markup=keyboard_builder(["Я авторизовался ✅"]))
    await state.update_data(start_greet=start_message)


@callback_router.callback_query(BotStates.choosing_action)
@auth_check
async def choose_action(query: CallbackQuery, state: FSMContext):
    """Handle user action choice"""
    if query.data == "Узнать складские остатки":
        await state.set_state(BotStates.stock_remains_item)
        remain_item_message = await query.message.edit_text(
            "Введите название товара, чтобы узнать его остаток на складе.",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_ask_item=remain_item_message)
    elif query.data == "Отслеживать товары":
        track_list = get_users_tracks(query.from_user.id)
        if track_list:
            await state.update_data(track_prod_list=track_list)
            await state.update_data(track_page=1)
            products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(track_list[:5]))
            if len(track_list) < 6:
                await query.message.edit_text(
                    "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                    reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "Вернуться назад↩️"]))
            else:
                await query.message.edit_text(
                    "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                    reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "1/" +
                                                   str(math.ceil(len(track_list) / 5)), "→", "Вернуться назад↩️"],
                                                  [1, 1, 2, 1]))
        else:
            await query.message.edit_text(
                "<b>У Вас пока что нет отслеживаемых товаров.</b>\n\nЧтобы добавить товар воспользуйтесь кнопками "
                "ниже.", reply_markup=keyboard_builder(["Добавить товар", "Вернуться назад↩️"]), parse_mode="HTML")
            await state.update_data(track_prod_list=[])
            await state.update_data(track_page=1)
        await state.set_state(BotStates.choosing_track_action)
    else:
        await state.set_state(BotStates.prediction_item)
        predict_item_message = await query.message.edit_text(
            "Введите название товара для которого необходимо сформировать прогноз.",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(predict_params_propose=predict_item_message)


@callback_router.callback_query(BotStates.stock_remains_item)
@auth_check
async def stock_return_back(query: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.choosing_action)
    ask_message = await query.message.edit_text(
        "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
        "хотите сделать сообщением.", parse_mode="html",
        reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз", "Отслеживать товары"]))
    await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.prediction_item)
@auth_check
async def predict_return_back(query: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.choosing_action)
    ask_message = await query.message.edit_text(
        "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
        "хотите сделать сообщением.", parse_mode="html",
        reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз", "Отслеживать товары"]))
    await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.asking_prediction)
@auth_check
async def ask_prediction(query: CallbackQuery, state: FSMContext):
    if query.data == "Сформировать прогноз":
        await query.message.edit_text(query.message.text)
        await state.set_state(BotStates.asking_predict_period)
        await query.message.answer("На какой период вы хотите сформировать прогноз? Выберите ниже либо напишите "
                                   "сообщением.", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    else:
        await query.message.edit_text(query.message.text)
        await state.set_state(BotStates.stock_remains_item)
        remain_item_message = await query.message.edit_text(
            "Введите название товара, чтобы узнать его остаток на складе.",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_ask_item=remain_item_message)


@callback_router.callback_query(BotStates.remain_choosing_good)
@auth_check
async def stock_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["remains_products"]
    product_index = int(query.data) - 1
    chosen_product = product_list[product_index]
    await state.update_data(chosen_product=chosen_product)
    await query.message.edit_text("Был выбран товар:\n\n<b>" + chosen_product + "</b>", parse_mode="HTML")
    remains_response = get_remains(chosen_product)
    await query.message.answer_photo(photo=FSInputFile(remains_response["file_name"]))
    await state.set_state(BotStates.choosing_predict)
    os.remove(remains_response["file_name"])
    await query.message.answer(remains_response["message"], reply_markup=keyboard_builder(["Сформировать прогноз",
                                                                                           "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.choosing_predict)
@auth_check
async def choose_forecast(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Сформировать прогноз":
        await state.set_state(BotStates.choosing_predict_period)
        await query.message.answer("На какой период вы хотите сформировать прогноз?",
                                   reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    else:
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.answer(
            "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
            "хотите сделать сообщением.", parse_mode="html",
            reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз", "Отслеживать товары"]))
        await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.predict_choosing_good)
@auth_check
async def predict_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["prediction_products"]
    product_index = int(query.data) - 1
    chosen_product = product_list[product_index]
    await state.update_data(chosen_product=chosen_product)
    await query.message.edit_text("Был выбран товар:\n\n<b>" + chosen_product + "</b>", parse_mode="HTML")
    await state.set_state(BotStates.choosing_predict_period)
    period_propose_message = await query.message.answer("На какой период вы хотите сформировать прогноз?",
                                                        reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    await state.update_data(period_propose=period_propose_message)


@callback_router.callback_query(BotStates.choosing_predict_period)
@auth_check
async def choose_predict_period(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("Период прогноза: <b>" + query.data + "</b>", parse_mode="HTML")
    user_data = await state.get_data()
    chosen_product = user_data["chosen_product"]
    n_months = {"месяц": 1, "квартал": 3, "год": 12}[query.data.lower()]
    response_data = get_prediction(chosen_product, n_months)
    await state.update_data(json_product=chosen_product)
    await state.update_data(json_period=n_months)
    await state.set_state(BotStates.asking_json)
    if not response_data["file_name1"] and not response_data["file_name2"]:
        await query.message.answer(response_data["message"],
                                   reply_markup=keyboard_builder(["Вернуться назад↩️"]))
    elif response_data["file_name1"] and not response_data["file_name2"]:
        await query.message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                         caption="Статистика по потреблению.")
        os.remove(response_data["file_name1"])
        await query.message.answer(response_data["message"],
                                   reply_markup=keyboard_builder(["Вернуться назад↩️"]))
    elif response_data["file_name1"] and response_data["file_name2"]:
        await query.message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                         caption="Статистика по потреблению.")
        os.remove(response_data["file_name1"])
        await query.message.answer_photo(photo=FSInputFile(response_data["file_name2"]),
                                         caption="Прогнозируемое потребление товара.")
        os.remove(response_data["file_name2"])
        if response_data["message"] == "На складе имеется достаточное количество товаров для данного срока.":
            await state.update_data(json_num=0)
        else:
            await state.update_data(json_num=response_data["message"].split(" ")[2])
        await query.message.answer(response_data["message"],
                                   reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.asking_json)
@auth_check
async def ask_json(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Сформировать закупку":
        user_data = await state.get_data()
        start_date = "08.01.2022"
        end_date = datetime(2022, 1, 8) + relativedelta(months=user_data["json_period"])
        json_data = get_json(user_data["json_product"], query.from_user.id, int(user_data["json_num"]), start_date,
                             end_date.strftime("%d.%m.%Y"))
        if json_data["has_warning"]:
            await query.message.answer("Возможно данная закупка не соответствует 44-ФЗ.")
        del json_data["has_warning"]
        json_name = "temp_files/" + str(time.time_ns()) + '.json'
        with open(json_name, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        await state.update_data(json_data=json_data)
        await state.set_state(BotStates.asking_editing_fields)
        await query.message.answer_document(
            document=FSInputFile(json_name, filename="Закупка" + str(json_data["id"]) + ".json"),
            caption="Файл со сформированной закупкой.",
            reply_markup=keyboard_builder(["Редактировать поля", "Вернуться назад↩️"]))
        os.remove(json_name)
    else:
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.answer(
            "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы хотите сделать сообщением.",
            parse_mode="html", reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                                              "Отслеживать товары"]))
        await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.nlp_predict_choosing_good)
@auth_check
async def nlp_forecast_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["prediction_products"]
    product_index = int(query.data) - 1
    chosen_product = product_list[product_index]
    await state.update_data(chosen_product=chosen_product)
    await query.message.edit_text("Был выбран товар:\n\n<b>" + chosen_product + "</b>", parse_mode="HTML")
    await query.message.answer("Период прогноза: <b>" + str(user_data["n_months"]) + " мес.</b>", parse_mode="HTML")
    prediction_response = get_prediction(chosen_product, user_data["n_months"])
    await state.update_data(json_product=chosen_product)
    await state.update_data(json_period=user_data["n_months"])
    await state.set_state(BotStates.asking_json)
    if not prediction_response["file_name1"] and not prediction_response["file_name2"]:
        await query.message.answer(prediction_response["message"], reply_markup=keyboard_builder(["Вернуться назад↩️"]))
    elif prediction_response["file_name1"] and not prediction_response["file_name2"]:
        await query.message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                         caption="Статистика по потреблению.")
        os.remove(prediction_response["file_name1"])
        await query.message.answer(prediction_response["message"],
                                   reply_markup=keyboard_builder(["Вернуться назад↩️"]))
    elif prediction_response["file_name1"] and prediction_response["file_name2"]:
        await query.message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                         caption="Статистика по потреблению.")
        os.remove(prediction_response["file_name1"])
        await query.message.answer_photo(photo=FSInputFile(prediction_response["file_name2"]),
                                         caption="Прогнозируемое потребление товара.")
        os.remove(prediction_response["file_name2"])
        if prediction_response["message"] == "На складе имеется достаточное количество товаров для данного срока.":
            await state.update_data(json_num=0)
        else:
            await state.update_data(json_num=prediction_response["message"].split(" ")[2])
        await query.message.answer(prediction_response["message"],
                                   reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.asking_editing_fields)
@auth_check
async def asking_editing_fields(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Редактировать поля":
        user_data = await state.get_data()
        json_data = user_data["json_data"]
        await state.update_data(edit_page=1)
        if json_data["id"]:
            switch_ans = await query.message.answer(
                'Поле "идентификатор расчета" имеет значение:\n' + str(json_data["id"]) +
                '\n\nЕсли Вы хотите изменить его, отправьте новое значение сообщением.\n\n<b>Для переключения '
                'между редактируемыми полями используйте кнопки ниже.</b>',
                parse_mode="HTML",
                reply_markup=keyboard_builder(["Закончить редактирование", "1/14", "→"], [1, 2]))
        else:
            switch_ans = await query.message.answer(
                'Поле "идентификатор расчета" не заполнено.\n\nЕсли Вы хотите заполнить его, отправьте '
                'значение сообщением.\n\n<b>Для переключения между редактируемыми полями используйте кнопки ниже.</b>',
                reply_markup=keyboard_builder(["Закончить редактирование", "1/14", "→"], [1, 2]), parse_mode="HTML")
        await state.update_data(switch_message=switch_ans)
        await state.set_state(BotStates.editing_fields)
    else:
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.answer(
            "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
            "хотите сделать сообщением.", parse_mode="html",
            reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз", "Отслеживать товары"]))
        await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.editing_fields)
@auth_check
async def edit_fields(query: CallbackQuery, state: FSMContext):
    """Handle editing of JSON fields"""
    user_data = await state.get_data()
    if query.data == "Закончить редактирование":
        await query.message.edit_text("Редактирование закончено")
        user_data = await state.get_data()
        json_data = user_data["json_data"]
        json_name = "temp_files/" + str(time.time_ns()) + '.json'
        with open(json_name, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        await state.set_state(BotStates.asking_editing_fields)
        await query.message.answer_document(
            document=FSInputFile(json_name, filename="Закупка" + str(json_data["id"]) + ".json"),
            caption="Файл со сформированной закупкой.",
            reply_markup=keyboard_builder(["Редактировать поля", "Вернуться назад↩️"]))
        os.remove(json_name)
    else:
        current_page = user_data["edit_page"]
        if query.data == str(current_page) + "/14":
            await query.answer(f"Вы находитесь на поле под номером {current_page} из 14")
        else:
            if query.data == "→":
                current_page += 1
            if query.data == "←":
                current_page -= 1
            json_data = user_data["json_data"]
            phrase_end = ('\n\nЕсли Вы хотите изменить его, отправьте новое значение сообщением.\n\n<b>Для переключения'
                          ' между редактируемыми полями используйте кнопки ниже.</b>')
            buttons_texts, size = ["Закончить редактирование", "←", str(current_page) + "/14", "→"], [1, 3]
            if current_page <= 3:
                current_value = json_data[JSON_PATHS[current_page - 1]]
                if current_page == 1:
                    del buttons_texts[1]
                    size = [1, 2]
            else:
                if current_page >= 10:
                    current_value = json_data['rows'][0][JSON_PATHS[current_page - 1]]
                    if current_page == 14:
                        del buttons_texts[3]
                        size = [1, 2]
                else:
                    splitted_path = JSON_PATHS[current_page - 1].split(".")
                    current_value = json_data['rows'][0]
                    for index in splitted_path:
                        current_value = current_value[index]
            if current_value:
                switch_ans = await query.message.edit_text(
                    'Поле "' + JSON_FIELDS[current_page - 1] + '" имеет значение:\n' + str(current_value) +
                    phrase_end, parse_mode="HTML",
                    reply_markup=keyboard_builder(buttons_texts, size))
            else:
                switch_ans = await query.message.edit_text(
                    'Поле "' + JSON_FIELDS[current_page - 1] + '" не заполнено' + phrase_end, parse_mode="HTML",
                    reply_markup=keyboard_builder(buttons_texts, size))
            await state.update_data(switch_message=switch_ans)
            await state.update_data(edit_page=current_page)


@callback_router.callback_query(BotStates.admin_choosing_action)
@auth_check
async def admin_choose_good(query: CallbackQuery, state: FSMContext):
    """Handler for admin choosing action"""
    if query.data == "Загрузить складские остатки":
        await query.message.edit_text("Загрузите файл, содержащий складские остатки в формате xlsx.")
        await state.set_state(BotStates.loading_remainings)
    else:
        await query.message.edit_text("Загрузите файл, содержащий обороты по счету в формате xlsx.")
        await state.set_state(BotStates.loading_turnover)


@callback_router.callback_query(BotStates.choosing_track_action)
@auth_check
async def choose_track_action(query: CallbackQuery, state: FSMContext):
    """Handler for choosing action in tracking product menu"""
    user_data = await state.get_data()
    current_page = user_data["track_page"]
    track_list = user_data["track_prod_list"]
    if query.data == "Добавить товар":
        await state.set_state(BotStates.adding_track_item)
        track_purpose = await query.message.edit_text(
            "Введите название товара для отслеживания:",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(track_purpose=track_purpose)
    elif query.data == "Удалить товар":
        start_index = (current_page - 1) * 5
        current_products = track_list[start_index:start_index + 5]
        n_products = len(current_products)
        products_text = "\n".join(f"<b>{i + 1}</b>. {track_list[i]}\n" for i in
                                  range(start_index, start_index + len(current_products)))
        await state.set_state(BotStates.track_deleting_item)
        await query.message.edit_text(
            "Пожалуйста, выберите товар для удаления из списка, нажав соответствующую кнопку с номером.\n\n" +
            products_text, parse_mode="HTML", reply_markup=keyboard_builder(
                [str(i) for i in range(start_index + 1, start_index + 1 + n_products)] +
                ["Вернуться назад↩️"], [n_products, 1]))
    elif query.data == "Вернуться назад↩️":
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.edit_text(
            "Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
            "хотите сделать сообщением.", parse_mode="html",
            reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз", "Отслеживать товары"]))
        await state.update_data(start_greet=ask_message)
    else:
        track_list = user_data["track_prod_list"]
        total_pages = math.ceil(len(track_list) / 5)
        if query.data == f"{current_page}/{total_pages}":
            await query.answer(f"Вы находитесь на странице под номером {current_page} из {total_pages}")
        else:
            if query.data == "→":
                current_page += 1
            if query.data == "←":
                current_page -= 1
            buttons_texts, size = (["Добавить товар", "Удалить товар", "←",
                                    f"{current_page}/{str(total_pages)}", "→", "Вернуться назад↩️"], [1, 1, 3, 1])
            if current_page == 1:
                del buttons_texts[2]
                size[2] = 2
            if current_page == total_pages:
                del buttons_texts[4]
                size[2] = 2
            start_index = (current_page - 1) * 5
            await state.update_data(track_page=current_page)
            current_products = track_list[start_index:start_index + 5]
            products_text = "\n".join(f"<b>{i + 1}</b>. {track_list[i]}\n" for i in
                                      range(start_index, start_index + len(current_products)))
            await query.message.edit_text(
                "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                reply_markup=keyboard_builder(buttons_texts, size))
            await state.set_state(BotStates.choosing_track_action)


@callback_router.callback_query(BotStates.track_deleting_item)
@auth_check
async def track_delete_item(query: CallbackQuery, state: FSMContext):
    """Handler to delete the item from tracking list"""
    user_data = await state.get_data()
    track_list = user_data["track_prod_list"]
    current_page = user_data["track_page"]
    start_index = (current_page - 1) * 5
    current_products = track_list[start_index:start_index + 5]
    if query.data == "Вернуться назад↩️":
        if track_list:
            await state.update_data(track_prod_list=track_list)
            await state.update_data(track_page=1)
            products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(track_list[:5]))
            if len(track_list) < 6:
                await query.message.edit_text(
                    "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                    reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "Вернуться назад↩️"]))
            else:
                await query.message.edit_text(
                    "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                    reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "1/" +
                                                   str(math.ceil(len(track_list) / 5)), "→", "Вернуться назад↩️"],
                                                  [1, 1, 2, 1]))
        else:
            await query.message.edit_text(
                "<b>У Вас пока что нет отслеживаемых товаров.</b>\n\nЧтобы добавить товар воспользуйтесь кнопками "
                "ниже.", reply_markup=keyboard_builder(["Добавить товар", "Вернуться назад↩️"]), parse_mode="HTML")
            await state.update_data(track_prod_list=[])
            await state.update_data(track_page=1)
        await state.set_state(BotStates.choosing_track_action)
    else:
        del_response = delete_track_product(query.from_user.id, track_list[int(query.data) - 1])
        if del_response:
            await query.message.delete()
            await query.message.answer("Товар был успешно удален.")
            del track_list[int(query.data) - 1]
            await state.update_data(track_prod_list=track_list)
        if len(current_products) == 1:
            current_page -= 1
            await state.update_data(track_page=current_page)
        start_index = (current_page - 1) * 5
        current_products = track_list[start_index:start_index + 5]
        total_pages = math.ceil(len(track_list) / 5)
        buttons_texts, size = (["Добавить товар", "Удалить товар", "←",
                                f"{current_page}/{str(total_pages)}", "→", "Вернуться назад↩️"], [1, 1, 3, 1])
        await state.set_state(BotStates.choosing_track_action)
        if total_pages == 0:
            await query.message.answer(
                "<b>У Вас пока что нет отслеживаемых товаров.</b>\n\nЧтобы добавить товар воспользуйтесь кнопками "
                "ниже.", reply_markup=keyboard_builder(["Добавить товар", "Вернуться назад↩️"]), parse_mode="HTML")
            return
        if total_pages == 1:
            buttons_texts, size = ["Добавить товар", "Удалить товар", "Вернуться назад↩️"], [1, 1, 1]
        elif current_page == 1:
            del buttons_texts[2]
            size[2] = 2
        elif current_page == total_pages:
            del buttons_texts[4]
            size[2] = 2
        products_text = "\n".join(f"<b>{i + 1}</b>. {track_list[i]}\n" for i in
                                  range(start_index, start_index + len(current_products)))
        await state.set_state(BotStates.choosing_track_action)
        await query.message.answer(
            "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder(buttons_texts, size))


@callback_router.callback_query(BotStates.inserting_track_item)
@auth_check
async def insert_track_item(query: CallbackQuery, state: FSMContext):
    """Handler to put the item to the tracking list"""
    user_data = await state.get_data()
    track_list = user_data["track_prod_list"]
    current_page = user_data["track_page"]
    total_pages = math.ceil(len(track_list) / 5)
    start_index = (current_page - 1) * 5
    current_products = track_list[start_index:start_index + 5]
    if query.data == "Вернуться назад↩️":
        products_text = "\n".join(f"<b>{i + 1}</b>. {track_list[i]}\n" for i in
                                  range(start_index, start_index + len(current_products)))
        buttons_texts, size = (["Добавить товар", "Удалить товар", "←",
                                f"{current_page}/{str(total_pages)}", "→", "Вернуться назад↩️"], [1, 1, 3, 1])
        if current_page == 1:
            del buttons_texts[2]
            size[2] = 2
        if current_page == total_pages:
            del buttons_texts[4]
            size[2] = 2
        await state.set_state(BotStates.choosing_track_action)
        await query.message.edit_text(
            "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder(buttons_texts, size))
    else:
        add_response = add_track_product(query.from_user.id, user_data["proposed_items"][int(query.data) - 1])
        if add_response:
            await query.message.delete()
            await query.message.answer("Товар был успешно добавлен.")
            track_list.append(user_data["proposed_items"][int(query.data) - 1])
            await state.update_data(track_prod_list=track_list)
            current_products = track_list[start_index:start_index + 5]
            total_pages = math.ceil(len(track_list) / 5)
        await state.set_state(BotStates.choosing_track_action)
        buttons_texts, size = (["Добавить товар", "Удалить товар", "←",
                                f"{current_page}/{str(total_pages)}", "→", "Вернуться назад↩️"], [1, 1, 3, 1])
        if total_pages == 1:
            buttons_texts, size = ["Добавить товар", "Удалить товар", "Вернуться назад↩️"], [1, 1, 1]
        elif current_page == 1:
            del buttons_texts[2]
            size[2] = 2
        elif current_page == total_pages:
            del buttons_texts[4]
            size[2] = 2
        products_text = "\n".join(f"<b>{i + 1}</b>. {track_list[i]}\n" for i in
                                  range(start_index, start_index + len(current_products)))
        await state.set_state(BotStates.choosing_track_action)
        await query.message.answer(
            "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder(buttons_texts, size))


@callback_router.callback_query(BotStates.adding_track_item)
@auth_check
async def add_track_item_back(query: CallbackQuery, state: FSMContext):
    """Handler to return back to menu from adding the track item"""
    track_list = get_users_tracks(query.from_user.id)
    if track_list:
        await state.update_data(track_prod_list=track_list)
        await state.update_data(track_page=1)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(track_list[:5]))
        if len(track_list) < 6:
            await query.message.edit_text(
                "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "Вернуться назад↩️"]))
        else:
            await query.message.edit_text(
                "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
                reply_markup=keyboard_builder(["Добавить товар", "Удалить товар", "1/" +
                                               str(math.ceil(len(track_list) / 5)), "→", "Вернуться назад↩️"],
                                              [1, 1, 2, 1]))
    else:
        await query.message.edit_text(
            "<b>У Вас пока что нет отслеживаемых товаров.</b>\n\nЧтобы добавить товар воспользуйтесь кнопками "
            "ниже.", reply_markup=keyboard_builder(["Добавить товар", "Вернуться назад↩️"]), parse_mode="HTML")
        await state.update_data(track_prod_list=[])
        await state.update_data(track_page=1)
    await state.set_state(BotStates.choosing_track_action)
