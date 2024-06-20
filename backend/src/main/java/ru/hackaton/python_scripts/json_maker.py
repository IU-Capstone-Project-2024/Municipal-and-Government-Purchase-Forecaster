import argparse
import json
import math
import os
import re

import pandas as pd


from pymongo import MongoClient


def find_OKPD(name):
    # Загрузка данных из CSV файла с кодами ОКПД-2
    df = pd.read_csv(
        '/backend/src/main/java/ru/hackaton/python_scripts/СТЕ_ОКПД-2.csv',
        encoding='utf-8')
    # Поиск номера ОКПД-2 по названию СТЕ
    res = df[df['Название СТЕ'] == name]
    okpd_number = 0 if len(res) == 0 else res['ОКПД-2'].values[0]
    return okpd_number


def get_settings_table():
    # Путь к папке с настроечными таблицами
    dir_path = '/backend/src/main/resources/Настроечные таблицы/'

    dfs = []
    # Инициализация пустого списка для хранения DataFrame
    for file in os.listdir(dir_path):
        # Чтение Excel файлов из указанной директории
        df = pd.read_excel(dir_path + file, sheet_name=None)
        dfs.extend([value for key, value in df.items() if value.shape[0] > 0])

    # Объединение всех DataFrame в один
    full_df = pd.concat(dfs, ignore_index=True)
    return full_df


def is_in_rules(name):
    # Получение полной таблицы настроек
    full_df = get_settings_table()
    flag = False
    okpd = find_OKPD(name)

    # Проверка наличия соответствия в правилах по ОКПД
    for index, row in full_df.iterrows():
        if isinstance(full_df.iloc[index, 1], str) and str(full_df.iloc[index, 1]) in str(okpd) and len(
                full_df.iloc[index, 1]) >= 5:
            flag = True
    return flag


def normalize_name(name):
    # Нормализация имени: приведение к нижнему регистру и удаление пробелов
    normalized_name = re.sub(r'\s+', '', name).strip().lower()
    return normalized_name


def make_json(params):
    """
    Создание JSON файла на основе прогноза
    :param params: массив параметров
    :return: None
    """

    entity_id, id_spgz, kpgz, char_in_str, end_price, si, okei_code = '', '', '', '', '', '', ''
    has_warning = False
    client = MongoClient('localhost', 27017)
    db = client['stock_remainings']
    collection = db['Справочники']

    data = None
    for doc in collection.find({'Название СТЕ': params[0]}):
        data = doc
        break
    if data is not None:
        if is_in_rules(params[0]):
            has_warning = True

        entity_id = data['СПГЗ код']

        id_spgz = data['СПГЗ']
        kpgz = data['Конечный код КПГЗ']

        characteristics = data['наименование характеристик'].split(';')
        char_in_str = ','.join(characteristics)

        if entity_id == 'NULL':
            entity_id = ''
            id_spgz = ''

        if kpgz == 'NULL':
            kpgz = ''

    new_colllection = db['Оборотная ведомость']
    data = new_colllection.find({'name': params[0]})
    document_to_use = None

    for document in data:
        quart = 0
        if int(document['квартал']) > quart:
            document_to_use = document

    if document_to_use is not None:
        price = [document_to_use['цена до'], document_to_use['цена после'], document_to_use['цена кредит во'],
                 document_to_use['цена дебет во']]

        end_price = 0

        for value in price:
            if not math.isnan(value):
                end_price = value
                break

        si = document_to_use['единица измерения']
        okei_code = 0
        if si == 'шт' or si == 'шт.':
            okei_code = '796'
        elif si == 'упак' or si == 'упак.':
            okei_code = '778'
        elif si == 'пар' or si == 'пар.':
            okei_code = '715'
        elif si == 'пач' or si == 'пач.' or si == 'пачка':
            okei_code = '728'
        elif si == 'к-т' or si == 'компл.' or si == 'компл.':
            okei_code = '839'
        elif si == 'рул' or si == 'рул.':
            okei_code = '736'
        elif si == 'м3':
            okei_code = '113'
        elif si == 'кг' or si == 'кг.':
            okei_code = '166'
        elif si == 'м' or si == 'м.':
            okei_code = '006'
        elif si == 'набор':
            okei_code = '704'
        else:
            okei_code = ''

    # Создание словаря для генерации JSON
    data = {
        "has_warning": has_warning,
        "id": params[1],
        "lotEntityId": "",
        "CustomerId": params[2],
        "rows": [
            {
                "DeliverySchedule": {
                    "dates": {
                        "end_date": params[5],
                        "start_date": params[4]
                    },
                    "deliveryAmount": params[3],
                    "deliveryConditions": "",
                    "year": params[5][-4:],
                },
                "address": {
                    "gar_id": "",  # Задается в ручную
                    "text": ""  # Задается в ручную
                },
                "entityId": entity_id,
                "id": id_spgz,
                "nmc": end_price * params[3],
                "okei_code": si,
                "purchaseAmount": params[3],
                "spgzCharacteristics": [
                    {
                        "characteristicName": char_in_str,
                        "characteristicSpgzEnums": [
                            {"value": "value1"}
                        ],
                        "conditionTypeId": '',
                        "kpgzCharacteristicId": kpgz,
                        "okei_id": okei_code,
                        "selectType": '',
                        "typeId": '',
                        "value1": 'value1',

                    }
                ]
            }
        ]
    }
    print(json.dumps(data))


def main():
    parser = argparse.ArgumentParser(description='Обработка аргументов.')
    parser.add_argument('item_name', type=str)
    parser.add_argument('id', type=int)
    parser.add_argument('user_id', type=int)
    parser.add_argument('predict', type=int)
    parser.add_argument('start_date', type=str)
    parser.add_argument('end_date', type=str)
    args = parser.parse_args()
    make_json([normalize_name(args.item_name), args.id, args.user_id, args.predict, args.start_date, args.end_date])


if __name__ == '__main__':
    main()
