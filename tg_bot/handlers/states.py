from aiogram.fsm.state import StatesGroup, State


class BotStates(StatesGroup):
    checking_auth = State()
    choosing_action = State()
    stock_remains_item = State()
    predict_item = State()
    asking_prediction = State()
    identifying_period = State()
    remain_choosing_good = State()
    forecast_choosing_good = State()
    asking_json = State()
    choosing_period = State()
    editing_fields = State()
    choosing_forecast = State()
    no_prediction = State()
    nlp_forecast_choosing_good = State()
    admin_choosing_action = State()
    loading_remainings = State()
    loading_turnover = State()
    recording_value = State()
    switching_fields = State()