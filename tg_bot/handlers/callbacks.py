import json
import os
import time
import uuid
from datetime import datetime

from functools import wraps

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from os import getenv

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, is_refresh_expired, delete_token, \
    is_token_expired, refresh_token, get_roles
from handlers.states import BotStates

from aiogram_bot.utils.backend_methods import get_remains, get_forecast, get_json

load_dotenv(dotenv_path="../tg_conf.env")

AUTH_URL = getenv('AUTH_URL')

callback_router = Router()

JSON_ENDPOINTS = ["id", "lotEntityId", "CustomerId", "end_date", "start_date", "deliveryAmount", "deliveryConditions", "year", "gar_id", "text", "entityId", "nmc", "okei_code", "purchaseAmount"]

def auth_check(func):
    @wraps(func)
    async def wrapper(query: CallbackQuery, state: FSMContext, *args, **kwargs):
        user_id = query.from_user.id
        if is_refresh_expired(user_id):
            delete_token(user_id)
            auth_state = str(uuid.uuid4())
            store_session(user_id, auth_state)
            await state.set_state(BotStates.checking_auth)
            await query.message.answer(
                f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                f"авторизации нажмите кнопку ниже.</b>", parse_mode="html")

        else:
            if is_token_expired(user_id):
                refresh_token(user_id)
            return await func(query, state, *args, **kwargs)
    return wrapper


@callback_router.callback_query(BotStates.checking_auth)
async def check_authorization(query: CallbackQuery, state: FSMContext):
    if get_token(query.from_user.id):
        user_roles = get_roles(query.from_user.id)
        if user_roles and "tg_admin" in user_roles:
            await query.message.delete()
            await state.set_state(BotStates.admin_choosing_action)
            admin_greet = await query.message.answer(
                "<b>Добро пожаловать в Админ-панель бота для автоматизации покупок!</b>\n\nПожалуйста, выберите одно из предложенных ниже действий.",
                parse_mode="html",
                reply_markup=keyboard_builder(["Загрузить складские остатки",
                                               "Загрузить обороты по счету"]))
            await state.update_data(admin_greet=admin_greet)
        else:
            await query.message.delete()
            await state.set_state(BotStates.choosing_action)
            await query.message.answer("<b>Вы успешно авторизовались в боте!</b>✅\n\nПожалуйста, выберите одно из "
                                       "предложенных ниже действий или опишите, что Вы хотите сделать сообщением.",
                                       reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]),
                                       parse_mode="HTML")

    else:
        await query.message.delete()
        auth_state = str(uuid.uuid4())
        store_session(query.from_user.id, auth_state)
        start_no_auth = await query.message.answer(f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                                   f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                                   f"авторизации нажмите кнопку ниже.</b>", parse_mode="html",
                                   reply_markup=keyboard_builder(["Я авторизовался ✅"]))
        await state.update_data(start_greet=start_no_auth)


@callback_router.callback_query(BotStates.choosing_action)
@auth_check
async def choose_action(query: CallbackQuery, state: FSMContext):
    if query.data == "Узнать складские остатки":
        await state.set_state(BotStates.stock_remains_item)
        remaining_item = await query.message.edit_text(
            "Введите название товара, чтобы узнать его остаток на складе.",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_propose=remaining_item)
    else:
        await state.set_state(BotStates.predict_item)
        forecasting_item = await query.message.edit_text("Введите название товара для которого необходимо сформировать прогноз.",
                                      reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(forecast_propose=forecasting_item)


@callback_router.callback_query(BotStates.stock_remains_item)
@auth_check
async def stock_back_choose(query: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.choosing_action)
    ask_message = await query.message.edit_text("Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
                                  "хотите сделать сообщением.", parse_mode="html",
                                  reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
    await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.predict_item)
@auth_check
async def predict_back_choose(query: CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.choosing_action)
    ask_message = await query.message.edit_text("Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
                                  "хотите сделать сообщением.", parse_mode="html",
                                  reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
    await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.asking_prediction)
@auth_check
async def ask_prediction(query: CallbackQuery, state: FSMContext):
    if query.data == "Сформировать прогноз":
        await query.message.edit_text(query.message.text)
        await state.set_state(BotStates.identifying_period)
        await query.message.answer("На какой период вы хотите сформировать прогноз? Выберите ниже либо напишите "
                                   "сообщением.", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    else:
        await query.message.edit_text(query.message.text)
        await state.set_state(BotStates.stock_remains_item)
        propose_message = await query.message.edit_text(
            "Введите название товара, чтобы узнать его остаток на складе.",
            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_propose=propose_message)


@callback_router.callback_query(BotStates.remain_choosing_good)
@auth_check
async def remain_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["remain_products"]
    product_index = int(query.data) - 1
    await state.update_data(choosed_product=product_list[product_index])
    await query.message.edit_text("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
    desired_product = product_list[product_index]
    api_response = get_remains(desired_product)
    await query.message.answer_photo(photo=FSInputFile(api_response["file_name"]))
    await state.set_state(BotStates.choosing_forecast)
    os.remove(api_response["file_name"])
    await query.message.answer(api_response["message"], reply_markup=keyboard_builder(["Сформировать прогноз",
                                                                                 "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.choosing_forecast)
@auth_check
async def choose_forecast(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Сформировать прогноз":
        await state.set_state(BotStates.choosing_period)
        await query.message.answer("На какой период вы хотите сформировать прогноз?",
                                   reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    else:
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.answer("Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
                                      "хотите сделать сообщением.", parse_mode="html",
                                      reply_markup=keyboard_builder(
                                          ["Узнать складские остатки", "Сформировать прогноз"]))
        await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.forecast_choosing_good)
@auth_check
async def forecast_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["forecast_products"]
    product_index = int(query.data) - 1
    await state.update_data(choosed_product=product_list[product_index])
    await query.message.edit_text("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
    await state.set_state(BotStates.choosing_period)
    period_propose = await query.message.answer("На какой период вы хотите сформировать прогноз?", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
    await state.update_data(period_propose=period_propose)


@callback_router.callback_query(BotStates.choosing_period)
@auth_check
async def choose_period(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text("Период прогноза: <b>" + query.data + "</b>", parse_mode="HTML")
    user_data = await state.get_data()
    desired_product = user_data["choosed_product"]
    n_months = {"месяц": 1, "квартал": 3, "год": 12}[query.data.lower()]
    response_data = get_forecast(desired_product, n_months)
    await state.update_data(json_product=desired_product)
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
        await query.message.answer_photo(photo=FSInputFile(response_data["file_name1"]), caption="Статистика по потреблению.")
        os.remove(response_data["file_name1"])
        await query.message.answer_photo(photo=FSInputFile(response_data["file_name2"]), caption="Прогнозируемое потребление товара.")
        os.remove(response_data["file_name2"])
        await state.update_data(json_num=response_data["message"].split(" ")[2])
        await query.message.answer(response_data["message"], reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.asking_json)
@auth_check
async def ask_json(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Сформировать закупку":
        user_data = await state.get_data()
        end_date = datetime(2022, 1, 8) + relativedelta(months=user_data["json_period"])
        json_data = get_json(user_data["json_product"], query.from_user.id, int(user_data["json_num"]), "08.01.2022", end_date.strftime("%d.%m.%Y"))
        if json_data["has_warning"]:
            await query.message.answer("Возможно данная закупка не соответствует 44-ФЗ.")
        del json_data["has_warning"]
        json_name = "temp_files/" + str(time.time_ns()) + '.json'
        with open(json_name, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        await state.update_data(json_data=json_data)
        await state.set_state(BotStates.editing_fields)
        await query.message.answer_document(document=FSInputFile(json_name, filename="Закупка" + str(json_data["id"]) + ".json"),
                                            caption="Файл со сформированной закупкой.", reply_markup=keyboard_builder(["Редактировать поля", "Вернуться назад↩️"]))
        os.remove(json_name)
    else:
        await state.set_state(BotStates.choosing_action)
        purpose_message = await query.message.answer("Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
                                      "хотите сделать сообщением.", parse_mode="html",
                                      reply_markup=keyboard_builder(
                                          ["Узнать складские остатки", "Сформировать прогноз"]))
        await state.update_data(no_auth_greet=purpose_message)


@callback_router.callback_query(BotStates.nlp_forecast_choosing_good)
@auth_check
async def nlp_forecast_choose_good(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["forecast_products"]
    product_index = int(query.data) - 1
    await state.update_data(choosed_product=product_list[product_index])
    await query.message.edit_text("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
    await query.message.answer("Период прогноза: <b>" + str(user_data["n_months"]) + " мес.</b>", parse_mode="HTML")
    desired_product = product_list[product_index]
    response_data = get_forecast(desired_product, user_data["n_months"])
    await state.update_data(json_product=desired_product)
    await state.set_state(BotStates.asking_json)
    await state.update_data(json_period=user_data["n_months"])
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
        await state.update_data(json_num=response_data["message"].split(" ")[2])
        await query.message.answer(response_data["message"],
                                   reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))


@callback_router.callback_query(BotStates.admin_choosing_action)
@auth_check
async def admin_choose_good(query: CallbackQuery, state: FSMContext):
    if query.data == "Загрузить складские остатки":
        await query.message.edit_text("Загрузите файл, содержащий складские остатки в формате xlsx.")
        await state.set_state(BotStates.loading_remainings)
    else:
        await query.message.edit_text("Загрузите файл, содержащий обороты по счету в формате xlsx.")
        await state.set_state(BotStates.loading_turnover)



@callback_router.callback_query(BotStates.editing_fields)
@auth_check
async def edit_fields(query: CallbackQuery, state: FSMContext):
    await query.message.delete_reply_markup()
    if query.data == "Редактировать поля":
        user_data = await state.get_data()
        json_data = user_data["json_data"]
        extracted_values = []
        for key in JSON_ENDPOINTS:
            if key in json_data:
                extracted_values.append(json_data[key])
            else:
                extracted_values.append(None)
        await state.update_data(current_pos=0)
        await state.update_data(extracted_values=extracted_values)
        await state.set_state(BotStates.recording_value)
        if extracted_values[0]:
            switch_ans = await query.message.answer("Поле " + JSON_ENDPOINTS[0] + " уже имеет значение:\n" +
                                                    str(extracted_values[0]) + "\n\nЕсли Вы хотите изменить его, "
                                                                           "отправьте новое значение\n\n<b>Для "
                                                                           "переключения редактируемого поля "
                                                                           "используйте кнопки ниже</b>",
                                                    reply_markup=keyboard_builder([">", "Закончить редактирование"], [1,2]), parse_mode="HTML")
        else:
            switch_ans = await query.message.answer("Поле " + str(JSON_ENDPOINTS[0]) + " не заполнено\n\nЕсли Вы хотите заполнить его, отправьте значение\n\n<b>Для переключения редактируемого поля используйте кнопки ниже</b>", parse_mode="HTML")
        await state.update_data(switch_mess=switch_ans)
    else:
        await state.set_state(BotStates.choosing_action)
        ask_message = await query.message.answer("Пожалуйста, выберите одно из предложенных ниже действий или опишите, что Вы "
                                      "хотите сделать сообщением.", parse_mode="html",
                                      reply_markup=keyboard_builder(
                                          ["Узнать складские остатки", "Сформировать прогноз"]))
        await state.update_data(start_greet=ask_message)


@callback_router.callback_query(BotStates.recording_value)
@auth_check
async def switch_fields(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    if query.data == "Закончить редактирование":
        json_data = user_data["json_data"]
        json_data_str = str(json_data)
        for i in range(len(JSON_ENDPOINTS)):
            start_index = json_data_str.index(JSON_ENDPOINTS[i]) + len(JSON_ENDPOINTS[i]) + 2
            end_index = start_index
            cur = ""
            while cur != ',' and cur != '}':
                end_index += 1
                cur = json_data_str[end_index]
            json_data_str = json_data_str[0:start_index] + " '" + user_data["extracted_values"][i] + "'" + json_data_str[end_index:]
        json_name = "temp_files/" + str(time.time_ns()) + '.json'
        normalized_json = json.loads(json_data_str.replace("'", '"'))
        with open(json_name, 'w', encoding='utf-8') as f:
            json.dump(normalized_json, f, ensure_ascii=False, indent=4)
        await state.update_data(json_data=normalized_json)
        await state.set_state(BotStates.editing_fields)
        await query.message.delete_reply_markup()
        await query.message.answer_document(
            document=FSInputFile(json_name, filename="Закупка" + str(user_data["extracted_values"][0]) + ".json"),
            caption="Файл со сформированной закупкой.",
            reply_markup=keyboard_builder(["Редактировать поля", "Вернуться назад↩️"]))
        os.remove(json_name)
    curr_pos = user_data["current_pos"]
    if query.data == ">":
        curr_pos += 1
    if query.data == "<":
        curr_pos -= 1
    switch_buttons, size = ["<", ">", "Закончить редактирование"], [2, 2]
    if curr_pos == 0:
        switch_buttons.remove("<")
        size = [1, 2]
    elif curr_pos == len(JSON_ENDPOINTS) - 1:
        switch_buttons.remove(">")
        size = [1, 2]
    if user_data["extracted_values"][curr_pos]:
        switch_ans = await query.message.edit_text("Поле " + JSON_ENDPOINTS[curr_pos] + " имеет значение:\n" +
                                                str(user_data["extracted_values"][curr_pos]) + "\n\nЕсли Вы хотите изменить его, "
                                                                            "отправьте новое значение\n\n<b>Для "
                                                                            "переключения редактируемого поля "
                                                                            "используйте кнопки ниже</b>",
                                                reply_markup=keyboard_builder(switch_buttons, size), parse_mode="HTML")
    else:
        switch_ans = await query.message.edit_text("Поле " + str(
            JSON_ENDPOINTS[curr_pos]) + " не заполнено\n\nЕсли Вы хотите заполнить его, отправьте значение\n\n<b>Для переключения редактируемого поля используйте кнопки ниже</b>",
                                reply_markup=keyboard_builder(switch_buttons,size), parse_mode="HTML")
    await state.update_data(switch_mess=switch_ans)
    await state.update_data(current_pos=curr_pos)
