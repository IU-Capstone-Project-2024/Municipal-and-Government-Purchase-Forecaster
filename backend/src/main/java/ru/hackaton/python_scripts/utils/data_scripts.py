from re import sub
from os import getenv
from datetime import datetime
from dotenv import load_dotenv

from pymongo import MongoClient
import pandas as pd

from utils.time_scripts import make_datetime

load_dotenv(dotenv_path="py_prediction.env")

MONGO_URL="mongodb://localhost:27017"
DB_NAME="stock_remainings"


# Функция чтобы найти все вхождения в коллекцию по фильтру
def mongo_find(filter):
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection_ost = db['Складские остатки']
    data = collection_ost.find(filter)
    return data


# Функция для вставки данных, если записи еще не существует
def insert_data_if_not_exists(name, normalized_name):
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db['Нормализированные имена']
    existing_document = collection.find_one({'name': name})
    if not existing_document:
        data = {
            'name': name,
            'normalized_name': normalized_name,
        }
        collection.insert_one(data)


def get_mongo_collection(collection_name):
    """
    Возвращает коллекцию MongoDB

    :return: Коллекция MongoDB
    """
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    return db[collection_name]


def normalize_name(name):
    # Приводим к нижнему регистру и удаляем пробелы
    normalized_name = sub(r'\s+', '', name).strip().lower()
    insert_data_if_not_exists(name, normalized_name)
    return normalized_name


def fetch_data(collection, name):
    """
    Получает данные из коллекции MongoDB и нормализует имена.

    :param collection: Коллекция MongoDB
    :param name: Название для нормализации
    :return: Данные и даты
    """
    pipeline = [
        {
            "$project": {
                "год": {"$toString": "$год"},
                "квартал": "$квартал",
                "start_date": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": ["$квартал", "1"]}, "then": {"$concat": ["$год", "-03-31"]}},
                            {"case": {"$eq": ["$квартал", "2"]}, "then": {"$concat": ["$год", "-06-30"]}},
                            {"case": {"$eq": ["$квартал", "3"]}, "then": {"$concat": ["$год", "-09-30"]}},
                            {"case": {"$eq": ["$квартал", "4"]}, "then": {"$concat": ["$год", "-12-31"]}}
                        ],
                        "default": "unknown"
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$start_date"
            }
        },
        {
            "$project": {
                "date": "$_id"
            }
        }
    ]
    result = list(collection.aggregate(pipeline))
    dates = [doc['date'] for doc in result]
    data = collection.find({"name": normalize_name(name)})
    return data, dates


def aggregate_data(data, column):
    """
    Агрегирует данные по кварталам и годам.

    :param data: Исходные данные
    :return: Агрегированные данные
    """
    aggregated_data = {}
    for document in data:
        key = (document["квартал"], document["год"])
        if key not in aggregated_data:
            aggregated_data[key] = 0
        aggregated_data[key] += 0 if pd.isna(document[column]) else document[column]
    return aggregated_data


def create_dataframe(aggregated_data, columns):
    """
    Создает DataFrame из агрегированных данных.

    :param aggregated_data: Агрегированные данные
    :return: DataFrame
    """
    df = pd.DataFrame(
        [(value, make_datetime(key[0], key[1])) for key, value in aggregated_data.items()],
        columns=columns
    )
    return df


def add_missing_dates(df, dates, column):
    """
    Добавляет отсутствующие даты в DataFrame.

    :param column: Название колонки
    :param df: Исходный DataFrame
    :param dates: Список дат
    :return: DataFrame с добавленными отсутствующими датами
    """
    new_rows = []
    for date in dates:
        if date not in df['дата'].apply(lambda x: x.strftime('%Y-%m-%d')).values:
            new_rows.append({'дата': datetime.strptime(date, '%Y-%m-%d'), column: 0})
    if new_rows:
        new_rows_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_rows_df], ignore_index=True)
    return df