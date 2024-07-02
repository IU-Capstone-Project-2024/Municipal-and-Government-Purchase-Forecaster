import math
import os
import uuid
from dotenv import load_dotenv
from functools import wraps

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from utils.keyboards import keyboard_builder
from utils.auth_methods import get_token, store_session, is_refresh_expired, delete_token, \
    is_token_expired, refresh_token
from utils.backend_methods import get_remains, get_products, get_prediction, get_action_code, post_remainings, \
    post_turnovers, add_track_product
from handlers.states import BotStates

from bot_init import bot

# Load environment variables
load_dotenv("./tg_conf.env")
AUTH_URL = os.getenv('AUTH_URL')

message_router = Router()

# Fields for JSON processing
JSON_FIELDS = ['Идентификатор расчета', 'Идентификатор лота', 'Идентификатор заказчика', 'Дата начала поставки',
               'Дата окончания поставки', 'Объем поставки', 'Год', 'Идентификатор ГАР адреса',
               'Адрес в текстовой форме', 'Сквозной идентификатор СПГЗ', 'Идентификатор СПГЗ',
               'Сумма спецификации', 'Ед. измерения по ОКЕИ', 'Объем поставки']

JSON_PATHS = ['id', 'lotEntityId', 'CustomerId', 'DeliverySchedule.dates.start_date', 'DeliverySchedule.dates.end_date',
              'DeliverySchedule.deliveryAmount', 'DeliverySchedule.year', 'address.gar_id', 'address.text', 'entityId',
              'id', 'nmc', 'okei_code', 'purchaseAmount']


def auth_check(func):
    """Decorator to check user authentication before executing a handler"""
    @wraps(func)
    async def wrapper(message: Message, state: FSMContext, *args, **kwargs):
        user_id = message.from_user.id
        if is_refresh_expired(user_id):
            delete_token(user_id)
            auth_state = str(uuid.uuid4())
            store_session(user_id, auth_state)
            await state.set_state(BotStates.checking_auth)
            await message.answer(
                f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, для "
                "того чтобы продолжить работу в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>",
                parse_mode="html", reply_markup=keyboard_builder(["Я авторизовался ✅"]))
            return
        else:
            if is_token_expired(user_id):
                refresh_token(user_id)
            return await func(message, state, *args, **kwargs)

    return wrapper


@message_router.message(BotStates.checking_auth)
async def check_authorization(message: Message, state: FSMContext):
    """Decorator to check user authentication before executing a handler"""
    user_data = await state.get_data()
    await user_data['start_greet'].edit_text(user_data['start_greet'].text)
    auth_state = str(uuid.uuid4())
    store_session(message.from_user.id, auth_state)
    no_auth_message = await message.answer(
        f"Вы не авторизованы ❌\n<a href='{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, для того чтобы "
        "продолжить работу в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>", parse_mode="html",
        reply_markup=keyboard_builder(["Я авторизовался ✅"]))
    await state.update_data(start_greet=no_auth_message)


@message_router.message(BotStates.authing_again)
async def auth_again(message: Message, state: FSMContext):
    """Handler for re-authorization"""
    user_data = await state.get_data()
    await user_data['start_greet'].edit_text(user_data['start_greet'].text)
    auth_state = str(uuid.uuid4())
    store_session(message.from_user.id, auth_state)
    await state.set_state(BotStates.checking_auth)
    start_message = await message.answer(
        f"<a href='{AUTH_URL + auth_state}'>Перейдите по ссылке для авторизации, для того чтобы продолжить работу "
        "в боте.</a>\n<b>После авторизации нажмите кнопку ниже.</b>", parse_mode="html",
        reply_markup=keyboard_builder(["Я авторизовался ✅"]))
    await state.update_data(start_greet=start_message)


@message_router.message(BotStates.choosing_action)
@auth_check
async def choose_action(message: Message, state: FSMContext):
    """Handler for choosing an action by natural language, encoded with digits"""
    user_data = await state.get_data()
    await user_data["start_greet"].edit_text(user_data["start_greet"].text)
    action_code = get_action_code(message.text)
    if action_code:
        code_parameters = [param.strip() for param in action_code.split(",")]
        if code_parameters[0] == '3' or len(code_parameters) != 3:
            ask_message = await message.answer(
                "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, что Вы хотите "
                "сделать.</b>", parse_mode="html",
                reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                               "Отслеживать товары"]))
            await state.update_data(start_greet=ask_message)
        elif code_parameters[0] == '2':
            if code_parameters[1] == "-" and code_parameters[2] == "-":
                await state.set_state(BotStates.prediction_item)
                predict_params_message = await message.edit_text(
                    "Введите название товара и период для которых необходимо сформировать прогноз.",
                    reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                await state.update_data(predict_params_propose=predict_params_message)
            elif code_parameters[1] != "-" and code_parameters[2] != "-":
                prediction_prod_list = get_products(code_parameters[1])
                if prediction_prod_list and len(prediction_prod_list) == 1:
                    await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" +
                                         prediction_prod_list[0] + "</b>", parse_mode="HTML")
                    n_months = math.ceil(int(code_parameters[2]) / 30)
                    await message.answer("Период прогноза: <b>" + str(n_months) + " мес.</b>", parse_mode="HTML")
                    prediction_response = get_prediction(prediction_prod_list[0], n_months)
                    await state.update_data(json_product=prediction_prod_list[0])
                    await state.update_data(json_period=n_months)
                    await state.set_state(BotStates.asking_json)
                    if not prediction_response["file_name1"] and not prediction_response["file_name2"]:
                        await message.answer(prediction_response["message"],
                                             reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                    elif prediction_response["file_name1"] and not prediction_response["file_name2"]:
                        await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                                   caption="Статистика по потреблению.")
                        os.remove(prediction_response["file_name1"])
                        await message.answer(prediction_response["message"],
                                             reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                    elif prediction_response["file_name1"] and prediction_response["file_name2"]:
                        await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                                   caption="Статистика по потреблению.")
                        os.remove(prediction_response["file_name1"])
                        await message.answer_photo(photo=FSInputFile(prediction_response["file_name2"]),
                                                   caption="Прогнозируемое потребление товара.")
                        os.remove(prediction_response["file_name2"])
                        if prediction_response["message"] == ("На складе имеется достаточное количество товаров для "
                                                              "данного срока."):
                            await state.update_data(json_num=0)
                        else:
                            await state.update_data(json_num=prediction_response["message"].split(" ")[2])
                        await message.answer(prediction_response["message"],
                                             reply_markup=keyboard_builder(
                                                 ["Сформировать закупку", "Вернуться назад↩️"]))
                elif prediction_prod_list:
                    await state.update_data(prediction_products=prediction_prod_list)
                    n_months = math.ceil(int(code_parameters[2]) / 30)
                    await state.update_data(n_months=n_months)
                    text_product_list = "\n".join(f"<b>{i + 1}</b>. {item}\n"
                                                  for i, item in enumerate(prediction_prod_list))
                    await state.set_state(BotStates.nlp_predict_choosing_good)
                    prod_list_len = len(prediction_prod_list)
                    if prod_list_len < 6:
                        buttons_size = [5, 1]
                    else:
                        buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
                    propose_goods_message = await message.answer(
                        "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
                        text_product_list, parse_mode="HTML",
                        reply_markup=keyboard_builder([str(i) for i in range(1, prod_list_len + 1)], buttons_size))
                    await state.update_data(propose_goods=propose_goods_message)
                else:
                    message_fail = await message.answer(
                        "<b>Данный товар не найден, выберите одно из предложенных ниже действий или опишите, "
                        "что Вы хотите сделать. Укажите название товара в кавычках и период прогноза в сообщении.</b>",
                        parse_mode="HTML",
                        reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                                       "Отслеживать товары"]))
                    await state.update_data(start_message=message_fail)
            else:
                message_fail = await message.answer(
                    "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, "
                    "что Вы хотите сделать. Укажите название товара в кавычках и период прогноза в сообщении.</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                                   "Отслеживать товары"]))
                await state.update_data(start_message=message_fail)
        if code_parameters[0] == '1':
            if code_parameters[1] == "-" and code_parameters[2] == "-":
                await state.set_state(BotStates.stock_remains_item)
                remain_item_message = await message.answer(
                    "Введите название товара, чтобы узнать его остаток на складе.",
                    reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                await state.update_data(remain_ask_item=remain_item_message)
            elif code_parameters[1] != "-" and code_parameters[2] == "-":
                remains_prod_list = get_products(code_parameters[1])
                if remains_prod_list and len(remains_prod_list) == 1:
                    await state.update_data(chosen_product=remains_prod_list[0])
                    await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" +
                                         remains_prod_list[0] + "</b>", parse_mode="HTML")
                    remains_response = get_remains(remains_prod_list[0])
                    await message.answer_photo(photo=FSInputFile(remains_response["file_name"]))
                    await state.set_state(BotStates.choosing_predict)
                    os.remove(remains_response["file_name"])
                    await message.answer(remains_response["message"],
                                         reply_markup=keyboard_builder(["Сформировать прогноз", "Вернуться назад↩️"]))
                elif remains_prod_list:
                    await state.update_data(remains_products=remains_prod_list)
                    text_product_list = "\n".join(f"<b>{i + 1}</b>. {item}\n"
                                                  for i, item in enumerate(remains_prod_list))
                    await state.set_state(BotStates.remain_choosing_good)
                    prod_list_len = len(remains_prod_list)
                    if prod_list_len < 6:
                        buttons_size = [5, 1]
                    else:
                        buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
                    await message.answer(
                        "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
                        text_product_list, parse_mode="HTML",
                        reply_markup=keyboard_builder([str(i) for i in range(1, prod_list_len + 1)], buttons_size))
                else:
                    message_fail = await message.answer(
                        "Данный товар не найден, пожалуйста введите название другого товара.",
                        reply_markup=keyboard_builder(["Вернуться назад↩️"]))
                    await state.update_data(remain_ask_item=message_fail)
            else:
                message_fail = await message.answer(
                    "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, "
                    "что Вы хотите сделать. Укажите название товара в кавычках и период прогноза в сообщении.</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                                   "Отслеживать товары"]))
                await state.update_data(start_message=message_fail)
    else:
        message_fail = await message.answer(
            "<b>Не понял Вас, выберите одно из предложенных ниже действий или опишите по-другому, "
            "что Вы хотите сделать. Укажите название товара в кавычках и период прогноза в сообщении.</b>",
            parse_mode="HTML",
            reply_markup=keyboard_builder(["Узнать складские остатки", "Сформировать прогноз",
                                           "Отслеживать товары"]))
        await state.update_data(start_message=message_fail)


@message_router.message(BotStates.stock_remains_item)
@auth_check
async def stock_remains(message: Message, state: FSMContext):
    """Handler for identifying item for stock balances"""
    user_data = await state.get_data()
    await user_data["remain_ask_item"].delete_reply_markup()
    remains_prod_list = get_products(message.text)
    if remains_prod_list and len(remains_prod_list) == 1:
        await state.update_data(chosen_product=remains_prod_list[0])
        await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" +
                             remains_prod_list[0] + "</b>", parse_mode="HTML")
        remains_response = get_remains(remains_prod_list[0])
        await message.answer_photo(photo=FSInputFile(remains_response["file_name"]))
        await state.set_state(BotStates.choosing_predict)
        os.remove(remains_response["file_name"])
        await message.answer(remains_response["message"], reply_markup=keyboard_builder(["Сформировать прогноз",
                                                                                         "Вернуться назад↩️"]))
    elif remains_prod_list:
        await state.update_data(remains_products=remains_prod_list)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(remains_prod_list))
        await state.set_state(BotStates.remain_choosing_good)
        prod_list_len = len(remains_prod_list)
        if prod_list_len < 6:
            buttons_size = [5, 1]
        else:
            buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
        await message.answer(
            "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, prod_list_len + 1)], buttons_size))
    else:
        fail_message = await message.answer("Данный товар не найден, пожалуйста введите название другого товара.",
                                            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(remain_ask_item=fail_message)
        await state.update_data(predict_params_propose=fail_message)


@message_router.message(BotStates.prediction_item)
@auth_check
async def prediction_item(message: Message, state: FSMContext):
    """Handler for choosing a product for prediction"""
    user_data = await state.get_data()
    await user_data["predict_params_propose"].edit_text(user_data["predict_params_propose"].text)
    predict_prod_list = get_products(message.text)
    if predict_prod_list and len(predict_prod_list) == 1:
        await state.update_data(chosen_product=predict_prod_list[0])
        await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" +
                             predict_prod_list[0] + "</b>", parse_mode="HTML")
        await state.set_state(BotStates.choosing_predict_period)
        period_propose = await message.answer("На какой период вы хотите сформировать прогноз?",
                                              reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(period_propose=period_propose)
    elif predict_prod_list:
        await state.update_data(prediction_products=predict_prod_list)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(predict_prod_list))
        await state.set_state(BotStates.predict_choosing_good)
        prod_list_len = len(predict_prod_list)
        if prod_list_len < 6:
            buttons_size = [5, 1]
        else:
            buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
        propose_goods = await message.answer(
            "<b>Пожалуйста, выберите товар из списка, нажав соответствующую кнопку с номером:</b>\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(predict_prod_list) + 1)], buttons_size))
        await state.update_data(propose_goods=propose_goods)
    else:
        fail_message = await message.answer("Данный товар не найден, пожалуйста введите название другого товара.",
                                            reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(predict_params_propose=fail_message)


@message_router.message(BotStates.predict_choosing_good)
@auth_check
async def predict_choose_good(message: Message, state: FSMContext):
    """Handler for actual choosing product among list of proposed"""
    user_data = await state.get_data()
    product_list = user_data["prediction_products"]
    edit_message = user_data['propose_goods']
    await edit_message.delete_reply_markup()
    if message.text in [str(i) for i in range(1, len(product_list) + 1)]:
        product_index = int(message.text) - 1
        await state.update_data(chosen_product=product_list[product_index])
        await edit_message.answer("Был выбран товар:\n\n<b>" + product_list[product_index] + "</b>", parse_mode="HTML")
        await state.set_state(BotStates.choosing_predict_period)
        period_propose = await edit_message.answer("На какой период вы хотите сформировать прогноз?",
                                                   reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(period_propose=period_propose)
    else:
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(product_list))
        prod_list_len = len(product_list)
        if prod_list_len < 6:
            buttons_size = [5, 1]
        else:
            buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
        propose_goods = await message.answer(
            "<b>Товара с таким номером нет\n\nПожалуйста, выберите товар из списка, нажав соответствующую кнопку с "
            "номером:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(product_list) + 1)], buttons_size))
        await state.update_data(propose_goods=propose_goods)


@message_router.message(BotStates.choosing_predict_period)
@auth_check
async def choose_period(message: Message, state: FSMContext):
    """Handler for choosing a period for prediction"""
    user_data = await state.get_data()
    desired_product = user_data["chosen_product"]
    period_message = user_data["period_propose"]
    await period_message.delete_reply_markup()
    if message.text.lower() in ["месяц", "квартал", "год"]:
        n_months = {"месяц": 1, "квартал": 3, "год": 12}[message.text.lower()]
        await message.answer("Период прогноза: <b>" + message.text.lower() + "</b>", parse_mode="HTML")
        prediction_response = get_prediction(desired_product, n_months)
        await state.update_data(json_period=n_months)
        await state.update_data(json_product=desired_product)
        await state.set_state(BotStates.asking_json)
        if not prediction_response["file_name1"] and not prediction_response["file_name2"]:
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif prediction_response["file_name1"] and not prediction_response["file_name2"]:
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                       caption="Статистика по потреблению.")
            os.remove(prediction_response["file_name1"])
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif prediction_response["file_name1"] and prediction_response["file_name2"]:
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                       caption="Статистика по потреблению.")
            os.remove(prediction_response["file_name1"])
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name2"]),
                                       caption="Прогнозируемое потребление товара.")
            os.remove(prediction_response["file_name2"])
            if prediction_response["message"] == "На складе имеется достаточное количество товаров для данного срока.":
                await state.update_data(json_num=0)
            else:
                await state.update_data(json_num=prediction_response["message"].split(" ")[2])
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))
    else:
        period_propose = await message.answer(
            "<b>Такого периода для прогноза нет.</b>\n\nВыберите пожалуйста период формирования прогноза из "
            "предложенных ниже вариантов.",
            parse_mode="HTML", reply_markup=keyboard_builder(["Месяц", "Квартал", "Год"]))
        await state.update_data(no_auth_greet=period_propose)


@message_router.message(BotStates.nlp_predict_choosing_good)
@auth_check
async def nlp_forecast_choose_good(message: Message, state: FSMContext):
    """Handler for choosing a product for prediction if request was by natural language"""
    user_data = await state.get_data()
    product_list = user_data["prediction_products"]
    edit_message = user_data['propose_goods']
    await edit_message.delete_reply_markup()
    if message.text in [str(i) for i in range(1, len(product_list) + 1)]:
        product_index = int(message.text) - 1
        chosen_product = product_list[product_index]
        await state.update_data(chosen_product=chosen_product)
        await edit_message.answer("Был выбран товар:\n\n<b>" + chosen_product + "</b>", parse_mode="HTML")
        await message.answer("Период прогноза: <b>" + str(user_data["n_months"]) + " мес.</b>", parse_mode="HTML")
        prediction_response = get_prediction(chosen_product, user_data["n_months"])
        await state.update_data(json_product=chosen_product)
        await state.update_data(json_period=user_data["n_months"])
        await state.set_state(BotStates.asking_json)
        if not prediction_response["file_name1"] and not prediction_response["file_name2"]:
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif prediction_response["file_name1"] and not prediction_response["file_name2"]:
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                       caption="Статистика по потреблению.")
            os.remove(prediction_response["file_name1"])
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        elif prediction_response["file_name1"] and prediction_response["file_name2"]:
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name1"]),
                                       caption="Статистика по потреблению.")
            os.remove(prediction_response["file_name1"])
            await message.answer_photo(photo=FSInputFile(prediction_response["file_name2"]),
                                       caption="Прогнозируемое потребление товара.")
            os.remove(prediction_response["file_name2"])
            if prediction_response["message"] == "На складе имеется достаточное количество товаров для данного срока.":
                await state.update_data(json_num=0)
            else:
                await state.update_data(json_num=prediction_response["message"].split(" ")[2])
            await message.answer(prediction_response["message"],
                                 reply_markup=keyboard_builder(["Сформировать закупку", "Вернуться назад↩️"]))
    else:
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(product_list))
        prod_list_len = len(product_list)
        if prod_list_len < 6:
            buttons_size = [5, 1]
        else:
            buttons_size = [prod_list_len // 2, prod_list_len - prod_list_len // 2]
        propose_goods = await message.answer(
            "<b>Товара с таким номером нет\n\nПожалуйста, выберите товар из списка, нажав соответствующую кнопку с "
            "номером:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, prod_list_len + 1)], buttons_size))
        await state.update_data(propose_goods=propose_goods)


@message_router.message(BotStates.admin_choosing_action)
@auth_check
async def admin_choose_action(message: Message, state: FSMContext):
    """Handler for choosing an action if user is logged as admin"""
    user_data = await state.get_data()
    await user_data["admin_greet"].delete_reply_markup()
    admin_greet = await message.answer(
        "<b>Не понял Ваш запрос.</b>\n\nПожалуйста, выберите одно из предложенных ниже действий.", parse_mode="html",
        reply_markup=keyboard_builder(["Загрузить складские остатки",
                                       "Загрузить обороты по счету"]))
    await state.update_data(admin_greet=admin_greet)


@message_router.message(BotStates.loading_remainings)
@auth_check
async def admin_load_remainings(message: Message, state: FSMContext):
    """Handler for loading new stock balances if user is logged as admin"""
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
    """Handler for loading new turnover if user is logged as admin"""
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


@message_router.message(BotStates.editing_fields)
@auth_check
async def edit_fields(message: Message, state: FSMContext):
    """Handler for editing fields in json manually"""
    user_data = await state.get_data()
    current_page = user_data["edit_page"]
    json_data = user_data["json_data"]
    buttons_texts, size = ["Закончить редактирование", "←", str(current_page) + "/14", "→"], [1, 3]
    if current_page <= 3:
        json_data[JSON_PATHS[current_page - 1]] = message.text
        if current_page == 1:
            del buttons_texts[1]
            size = [1, 2]
    else:
        if current_page >= 10:
            json_data['rows'][0][JSON_PATHS[current_page - 1]] = message.text
            if current_page == 14:
                del buttons_texts[3]
                size = [1, 2]
        else:
            splitted_path = JSON_PATHS[current_page - 1].split(".")
            if current_page <= 5:
                json_data['rows'][0][splitted_path[0]][splitted_path[1]][splitted_path[2]] = message.text
            else:
                json_data['rows'][0][splitted_path[0]][splitted_path[1]] = message.text
    await state.update_data(json_data=json_data)
    await user_data["switch_message"].edit_text('Значение поля "' + JSON_FIELDS[current_page - 1] + '" было изменено.')
    switch_ans = await message.answer(
        'Поле "' + JSON_FIELDS[current_page - 1] + '" теперь имеет значение:\n' + message.text + '\n\nЕсли Вы хотите '
        'изменить его, отправьте новое значение сообщением.\n\n<b>Для переключения между редактируемыми полями '
        'используйте кнопки ниже.</b>',
        parse_mode="HTML", reply_markup=keyboard_builder(buttons_texts, size))
    await state.update_data(switch_message=switch_ans)


@message_router.message(BotStates.adding_track_item)
@auth_check
async def add_track_item(message: Message, state: FSMContext):
    """Handler for adding new item for tracking its stock balances and """
    user_data = await state.get_data()
    track_list = user_data["track_prod_list"]
    current_page = user_data["track_page"]
    await user_data["track_purpose"].delete_reply_markup()
    items_add = get_products(message.text)
    if items_add and len(items_add) == 1:
        await state.update_data(track_chosen_product=items_add[0])
        await message.answer("Найден только 1 подходящий товар, поэтому он был выбран:\n\n<b>" +
                             items_add[0] + "</b>", parse_mode="HTML")
        add_response = add_track_product(message.from_user.id, items_add[0])
        if add_response:
            await message.answer("Товар был успешно добавлен.")
            track_list.append(items_add[0])
            await state.update_data(items_add=track_list)
        total_pages = math.ceil(len(track_list) / 5)
        start_index = (current_page - 1) * 5
        current_products = track_list[start_index:start_index + 5]
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
        await message.answer(
            "<b>Список товаров, для которых отслеживаются остатки:</b>\n\n" + products_text, parse_mode="HTML",
            reply_markup=keyboard_builder(buttons_texts, size))
    elif items_add:
        await state.update_data(proposed_items=items_add)
        products_text = "\n".join(f"<b>{i + 1}</b>. {item}\n" for i, item in enumerate(items_add))
        await state.set_state(BotStates.inserting_track_item)
        await message.answer(
            "Пожалуйста, выберите товар для добавления в список, нажав соответствующую кнопку с номером.\n\n" +
            products_text, parse_mode="HTML",
            reply_markup=keyboard_builder([str(i) for i in range(1, len(items_add) + 1)] + ["Вернуться назад↩️"],
                                          [len(items_add) // 2, len(items_add) - len(items_add) // 2, 1]))
    else:
        track_purpose = await message.answer("Данный товар не найден, пожалуйста введите название другого товара.",
                                             reply_markup=keyboard_builder(["Вернуться назад↩️"]))
        await state.update_data(track_purpose=track_purpose)
