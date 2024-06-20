import math
import os
import time
import uuid
from functools import wraps

from dotenv import load_dotenv
from os import getenv

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, is_refresh_expired, delete_token, \
    is_token_expired, refresh_token
from utils.backend_methods import get_remains, get_products, get_forecast, get_action_code, post_remainings, post_turnovers
from handlers.states import BotStates

from bot_init import bot

load_dotenv(dotenv_path="../tg_conf.env")

AUTH_URL = getenv('AUTH_URL')

message_router = Router()

JSON_ENDPOINTS = ["id", "lotEntityId", "CustomerId", "end_date", "start_date", "deliveryAmount", "deliveryConditions", "year", "gar_id", "text", "entityId", "nmc", "okei_code", "purchaseAmount"]

def auth_check(func):
    @wraps(func)
    async def wrapper(message: Message, state: FSMContext, *args, **kwargs):
        user_id = message.from_user.id
        if is_refresh_expired(user_id):
            delete_token(user_id)
            auth_state = str(uuid.uuid4())
            store_session(user_id, auth_state)
            await state.set_state(BotStates.checking_auth)
            await message.answer(
                f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                f"авторизации нажмите кнопку ниже.</b>", parse_mode="html")

        else:
            if is_token_expired(user_id):
                refresh_token(user_id)
            return await func(message, state, *args, **kwargs)

    return wrapper


@message_router.message(BotStates.checking_auth)
async def check_authorization(message: Message, state: FSMContext):
    user_data = await state.get_data()
    await user_data['start_greet'].edit_text(user_data['start_greet'].text)
    auth_state = str(uuid.uuid4())
    store_session(message.from_user.id, auth_state)
    start_no_auth = await message.answer(f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                                               f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                                               f"авторизации нажмите кнопку ниже.</b>", parse_mode="html",
                                               reply_markup=keyboard_builder(["Я авторизовался ✅"]))
    await state.update_data(start_greet=start_no_auth)


@message_router.message(BotStates.choosing_action)
async def choose_action(message: Message, state: FSMContext):
    if is_refresh_expired(message.from_user.id):
        delete_token(message.from_user.id)
        auth_state = str(uuid.uuid4())
        store_session(message.from_user.id, auth_state)
        await state.set_state(BotStates.checking_auth)
        await message.answer(f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите "
                             f"по ссылке для авторизации, для того чтобы продолжить работу в боте.</a>\n<b>После "
                             f"авторизации нажмите кнопку ниже.</b>", parse_mode="html",
                             reply_markup=keyboard_builder(["Я авторизовался ✅"]))
    else:
        if is_token_expired(message.from_user.id):
            refresh_token(message.from_user.id)
        user_data = await state.get_data()
        await user_data["no_auth_greet"].edit_text(user_data["no_auth_greet"].text)
        action_code = get_action_code(message.text)
        if action_code:
            await message.answer(action_code)
            code_with_params = action_code.split(",")
            for index in range(0, len(code_with_params)):
                code_with_params[index] = code_with_params[index].strip()
            if code_with_params[0] == '3' or len(code_with_params) != 3:
                message_fail = await message.answer(
                    "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, что Вы хотите сделать. </b>",
                    parse_mode="html",
                    reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
                await state.update_data(no_auth_greet=message_fail)
            if code_with_params[0] == '2':
                if code_with_params[1] == "-" and code_with_params[2] == "-":
                    await state.set_state(BotStates.predict_item)
                    forecasting_item = await message.edit_text(
                        "Введите название товара для которого необходимо сформировать прогноз.",
                        reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                    await state.update_data(forecast_propose=forecasting_item)
                elif code_with_params[1] != "-" and code_with_params[2] != "-":
                    forecast_prod_list = get_products(code_with_params[1])
                    if forecast_prod_list:
                        remain_list_len = len(forecast_prod_list)
                    else:
                        remain_list_len = 0
                    if remain_list_len == 1:
                        await message.answer(
                            "Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" + forecast_prod_list[
                                0] + "</b>",
                            parse_mode="HTML")
                        n_months = math.ceil(int(code_with_params[2])/30)
                        await message.answer("Период прогноза: <b>" + str(n_months) + " мес.</b>", parse_mode="HTML")
                        response_data = get_forecast(forecast_prod_list[0], n_months)
                        await state.update_data(json_product=forecast_prod_list[0])
                        await state.update_data(json_period=n_months)
                        await state.set_state(BotStates.asking_json)
                        if not response_data["file_name1"] and not response_data["file_name2"]:
                            await message.answer(response_data["message"],
                                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                        elif response_data["file_name1"] and not response_data["file_name2"]:
                            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                                       caption="Статистика по потреблению.")
                            os.remove(response_data["file_name1"])
                            await message.answer(response_data["message"],
                                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                        elif response_data["file_name1"] and response_data["file_name2"]:
                            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                                       caption="Статистика по потреблению.")
                            os.remove(response_data["file_name1"])
                            await message.answer_photo(photo=FSInputFile(response_data["file_name2"]),
                                                       caption="Прогнозируемое потребление товара.")
                            os.remove(response_data["file_name2"])
                            await state.update_data(json_num=response_data["message"].split(" ")[2])
                            await message.answer(response_data["message"],
                                                 reply_markup=keyboard_builder(
                                                     ["Сформировать закупку", "Вернуться назад↩️"]))

                    elif forecast_prod_list:
                        await state.update_data(forecast_products=forecast_prod_list)
                        n_months = math.ceil(int(code_with_params[2])/30)
                        await state.update_data(n_months=n_months)
                        products_text = "\n".join(
                            f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(forecast_prod_list))
                        await state.set_state(BotStates.nlp_forecast_choosing_good)
                        propose_goods = await message.answer(
                            "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
                            products_text, parse_mode="HTML",
                            reply_markup=keyboard_builder([str(i) for i in range(1, len(forecast_prod_list) + 1)],
                                                          [5, 1]))
                        await state.update_data(propose_goods=propose_goods)
                    else:
                        message_fail = await message.answer(
                            "<b>Данный товар не найден, выберите одно из предложенных ниже действий или опишите, что Вы хотите сделать, укажите название товара в кавычках и период прогноза в сообщении. </b>",
                            parse_mode="html",
                            reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))

                        await state.update_data(no_auth_greet=message_fail)

                else:
                    message_fail = await message.answer(
                        "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите, что Вы хотите сделать, укажите название товара в кавычках и период прогноза в сообщении. </b>",
                        parse_mode="html",
                        reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
                    await state.update_data(no_auth_greet=message_fail)
            if code_with_params[0] == '1':
                if code_with_params[1] == "-" and code_with_params[2] == "-":
                    await state.set_state(BotStates.stock_remains_item)
                    remaining_item = await message.answer(
                        "Введите название товара, чтобы узнать его остаток на складе.",
                        reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                    await state.update_data(remain_propose=remaining_item)
                elif code_with_params[1] != "-" and code_with_params[2] == "-":
                    remain_prod_list = get_products(code_with_params[1])
                    if remain_prod_list:
                        remain_list_len = len(remain_prod_list)
                    else:
                        remain_list_len = 0
                    if remain_list_len == 1:
                        await state.update_data(choosed_product=remain_prod_list[0])
                        await message.answer(
                            "Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" + remain_prod_list[
                                0] + "</b>",
                            parse_mode="HTML")
                        api_response = get_remains(remain_prod_list[0])
                        await message.answer_photo(photo=FSInputFile(api_response["file_name"]))
                        await state.set_state(BotStates.choosing_forecast)
                        os.remove(api_response["file_name"])
                        await message.answer(api_response["message"],
                                             reply_markup=keyboard_builder(["Сформировать прогноз",
                                                                            "Вернуться назад↩️"]))
                    elif remain_prod_list:
                        await state.update_data(remain_products=remain_prod_list)
                        products_text = "\n".join(
                            f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(remain_prod_list))
                        await state.set_state(BotStates.remain_choosing_good)
                        await message.answer(
                            "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
                            products_text, parse_mode="HTML",
                            reply_markup=keyboard_builder([str(i) for i in range(1, len(remain_prod_list) + 1)],
                                                          [5, 1]))
                    else:
                        not_found = await message.answer(
                            "Данный товар не найден, пожалуйста введите название другого товара.",
                            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                        await state.update_data(remain_propose=not_found)
                else:
                    message_fail = await message.answer(
                        "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите, что Вы хотите сделать, укажите название товара в кавычках и период прогноза в сообщении. </b>",
                        parse_mode="html",
                        reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
                    await state.update_data(no_auth_greet=message_fail)
        else:
            message_fail = await message.answer(
                "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, что Вы хотите сделать. </b>",
                parse_mode="html",reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз"]))
            await state.update_data(no_auth_greet=message_fail)


@message_router.message(BotStates.stock_remains_item)
@auth_check
async def stock_remains(message: Message, state: FSMContext):
    user_data = await state.get_data()
    await user_data["remain_propose"].edit_text(user_data["remain_propose"].text)
    remain_prod_list = get_products(message.text)
    if remain_prod_list:
        remain_list_len = len(remain_prod_list)
    else:
        remain_list_len = 0
    if remain_list_len == 1:
        await state.update_data(choosed_product=remain_prod_list[0])
        await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" + remain_prod_list[0] + "</b>",
                                      parse_mode="HTML")
        api_response = get_remains(remain_prod_list[0])
        await message.answer_photo(photo=FSInputFile(api_response["file_name"]))
        await state.set_state(BotStates.choosing_forecast)
        os.remove(api_response["file_name"])
        await message.answer(api_response["message"], reply_markup=keyboard_builder(["Сформировать прогноз",
                                                                                           "Вернуться назад↩️"]))
    elif remain_prod_list:
        await state.update_data(remain_products=remain_prod_list)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(remain_prod_list))
        await state.set_state(BotStates.remain_choosing_good)
        await message.answer("<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
                             products_text, parse_mode="HTML",
                             reply_markup=keyboard_builder([str(i) for i in range(1, len(remain_prod_list) + 1)], [5, 1]))
    else:
        not_found = await message.answer("Данный товар не найден, пожалуйста введите название другого товара.", reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_propose=not_found)


@message_router.message(BotStates.predict_item)
async def predict_choose_period(message: Message, state: FSMContext):
    user_data = await state.get_data()
    await user_data["forecast_propose"].edit_text(user_data["forecast_propose"].text)
    forecast_prod_list = get_products(message.text)
    if forecast_prod_list:
        remain_list_len = len(forecast_prod_list)
    else:
        remain_list_len = 0
    if remain_list_len == 1:
        await state.update_data(choosed_product=forecast_prod_list[0])
        await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" + forecast_prod_list[0] + "</b>",
                                      parse_mode="HTML")
        await state.set_state(BotStates.choosing_period)
        period_propose = await message.answer("На какой период вы хотите сформировать прогноз?",
                                                   reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(period_propose=period_propose)
    elif forecast_prod_list:
        await state.update_data(forecast_products=forecast_prod_list)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(forecast_prod_list))
        await state.set_state(BotStates.forecast_choosing_good)
        propose_goods = await message.answer(
            "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(forecast_prod_list) + 1)], [5, 1]))
        await state.update_data(propose_goods=propose_goods)
    else:
        not_found = await message.answer("Данный товар не найден, пожалуйста введите название другого товара.", reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(forecast_propose=not_found)


@message_router.message(BotStates.forecast_choosing_good)
@auth_check
async def forecast_choose_good(message: Message, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["forecast_products"]
    edit_message = user_data['propose_goods']
    await edit_message.delete_reply_markup()
    if message.text in [str(i) for i in range(1, len(product_list) + 1)]:
        product_index = int(message.text) - 1
        await state.update_data(choosed_product=product_list[product_index])
        await edit_message.answer("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
        await state.set_state(BotStates.choosing_period)
        period_propose = await edit_message.answer("На какой период вы хотите сформировать прогноз?", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(period_propose=period_propose)
    else:
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(product_list))
        propose_goods = await message.answer(
            "<b>Товара с таким номером нет\n\nПожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(product_list) + 1)], [5, 1]))
        await state.update_data(propose_goods=propose_goods)


@message_router.message(BotStates.choosing_period)
@auth_check
async def choose_period(message: Message, state: FSMContext):
    user_data = await state.get_data()
    desired_product = user_data["choosed_product"]
    period_message = user_data["period_propose"]
    await period_message.delete_reply_markup()
    if message.text.lower() in ["месяц", "квартал", "год"]:
        n_months = {"месяц": 1, "квартал": 3, "год": 12}[message.text.lower()]
        await message.answer("Период прогноза: <b>" + message.text.lower() + "</b>", parse_mode="HTML")
        response_data = get_forecast(desired_product, n_months)
        await state.update_data(json_period=n_months)
        await state.update_data(json_product=desired_product)
        await state.set_state(BotStates.asking_json)
        if not response_data["file_name1"] and not response_data["file_name2"]:
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif response_data["file_name1"] and not response_data["file_name2"]:
            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                             caption="Статистика по потреблению.")
            os.remove(response_data["file_name1"])
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif response_data["file_name1"] and response_data["file_name2"]:
            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                             caption="Статистика по потреблению.")
            os.remove(response_data["file_name1"])
            await message.answer_photo(photo=FSInputFile(response_data["file_name2"]),
                                             caption="Прогнозируемое потребление товара.")
            os.remove(response_data["file_name2"])
            await state.update_data(json_num=response_data["message"].split(" ")[2])
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))
    else:
        period_propose = await message.answer("<b>Такого периода для прогноза нет.</b>\n\nВыберите пожалуйста период формирования прогноза из предложенных ниже вариантов.", parse_mode="HTML", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(no_auth_greet=period_propose)


@message_router.message(BotStates.nlp_forecast_choosing_good)
@auth_check
async def nlp_forecast_choose_good(message: Message, state: FSMContext):
    user_data = await state.get_data()
    product_list = user_data["forecast_products"]
    edit_message = user_data['propose_goods']
    await edit_message.delete_reply_markup()
    if message.text in [str(i) for i in range(1, len(product_list) + 1)]:
        product_index = int(message.text) - 1
        await state.update_data(choosed_product=product_list[product_index])
        await edit_message.answer("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
        await message.answer("Период прогноза: <b>" + str(user_data["n_months"]) + " мес.</b>", parse_mode="HTML")
        desired_product = product_list[product_index]
        response_data = get_forecast(desired_product, user_data["n_months"])
        await state.update_data(json_product=desired_product)
        await state.set_state(BotStates.asking_json)
        await state.update_data(json_period=user_data["n_months"])
        if not response_data["file_name1"] and not response_data["file_name2"]:
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif response_data["file_name1"] and not response_data["file_name2"]:
            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                             caption="Статистика по потреблению.")
            os.remove(response_data["file_name1"])
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif response_data["file_name1"] and response_data["file_name2"]:
            await message.answer_photo(photo=FSInputFile(response_data["file_name1"]),
                                             caption="Статистика по потреблению.")
            os.remove(response_data["file_name1"])
            await message.answer_photo(photo=FSInputFile(response_data["file_name2"]),
                                             caption="Прогнозируемое потребление товара.")
            os.remove(response_data["file_name2"])
            await state.update_data(json_num=response_data["message"].split(" ")[2])
            await message.answer(response_data["message"],
                                       reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))
    else:
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(product_list))
        propose_goods = await message.answer(
            "<b>Товара с таким номером нет\n\nПожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(product_list) + 1)], [5, 1]))
        await state.update_data(propose_goods=propose_goods)


@message_router.message(BotStates.admin_choosing_action)
@auth_check
async def admin_choose_action(message: Message, state: FSMContext):
    user_data = await state.get_data()
    await user_data["admin_greet"].delete_reply_markup()
    admin_greet = await message.answer("<b>Не понял Ваш запрос.</b>\n\nПожалуйста, выберите одно из предложенных ниже действий.", parse_mode="html",
                                             reply_markup=keyboard_builder(["Загрузить складские остатки",
                                                                            "Загрузить обороты по счету"]))
    await state.update_data(admin_greet=admin_greet)


@message_router.message(BotStates.loading_remainings)
@auth_check
async def admin_load_remainings(message: Message, state: FSMContext):
    if message.document.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = "temp_files/" + message.document.file_name
        await bot.download_file(file.file_path, file_path)
        response_message = post_remainings(file_path)
        await message.answer(response_message)
        await state.set_state(BotStates.admin_choosing_action)
        admin_greet = await message.answer(
            "Пожалуйста, выберите одно из предложенных ниже действий.",
            parse_mode="html",
            reply_markup=keyboard_builder(["Загрузить складские остатки",
                                           "Загрузить обороты по счету"]))
        await state.update_data(admin_greet=admin_greet)
    else:
        await message.answer("Можно загрузить только файлы в формате xlsx, попробуйте еще раз.")


@message_router.message(BotStates.loading_turnover)
@auth_check
async def admin_load_turnover(message: Message, state: FSMContext):
    if message.document.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = "temp_files/" + message.document.file_name
        await bot.download_file(file.file_path, file_path)
        response_message = post_turnovers(file_path)
        await message.answer(response_message)
        await state.set_state(BotStates.admin_choosing_action)
        admin_greet = await message.answer(
            "Пожалуйста, выберите одно из предложенных ниже действий.",
            parse_mode="html",
            reply_markup=keyboard_builder(["Загрузить складские остатки",
                                           "Загрузить обороты по счету"]))
        await state.update_data(admin_greet=admin_greet)
    else:
        await message.answer("Можно загрузить только файлы в формате xlsx, попробуйте еще раз.")


@message_router.message(BotStates.recording_value)
@auth_check
async def record_value(message: Message, state: FSMContext):
    user_data = await state.get_data()
    curr_pos = user_data["current_pos"]
    json_data = user_data["extracted_values"]
    json_data[curr_pos] = message.text
    await state.update_data(json_data=json_data)
    await user_data["switch_mess"].edit_text("Значение поля было изменено")
    curr_pos = user_data["current_pos"]
    switch_buttons, size = ["<", ">", "Закончить редактирование"], [2, 2]
    if curr_pos == 0:
        switch_buttons.remove("<")
        size = [1, 2]
    elif curr_pos == len(JSON_ENDPOINTS) - 1:
        switch_buttons.remove(">")
        size = [1, 2]
    switch_ans = await message.answer("Поле " + JSON_ENDPOINTS[curr_pos] + " имеет значение:\n" +
                                               str(user_data["extracted_values"][
                                                       curr_pos]) + "\n\nЕсли Вы хотите изменить его, "
                                                                    "отправьте новое значение\n\n<b>Для "
                                                                    "переключения редактируемого поля "
                                                                    "используйте кнопки ниже</b>",
                                               reply_markup=keyboard_builder(switch_buttons, size), parse_mode="HTML")
    await state.update_data(switch_mess=switch_ans)
