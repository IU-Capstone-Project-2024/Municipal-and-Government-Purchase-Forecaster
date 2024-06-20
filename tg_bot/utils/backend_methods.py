import base64
import os
import time

import requests

from dotenv import load_dotenv
from os import getenv

# Load variables from the tg_conf.env file
load_dotenv(dotenv_path="tg_conf.env")

JAVA_BACKEND = getenv('JAVA_BACKEND')


def get_products(message):
    params = {'product': message}
    response = requests.get(JAVA_BACKEND + "/search-product", params=params)
    if response.status_code // 100 == 2:
        data = response.json()
        product_list = data
        return product_list
    return None


def get_remains(message):
    params = {'product': message}
    response = requests.get(JAVA_BACKEND + "/check-remainings", params=params)
    if response.status_code // 100 == 2:
        data = response.json()
        message = data['message']
        file_data = base64.b64decode(data['image'])
        file_name = "temp_files/" + str(time.time_ns()) + '.png'
        with open(file_name, 'wb') as f:
            f.write(file_data)
        return {'message': message, 'file_name': file_name}
    return None


def get_forecast(message, n_months):
    params = {'product': message, 'month': n_months}
    response = requests.get(JAVA_BACKEND + "/predict", params=params)
    if response.status_code // 100 == 2:
        data = response.json()
        message = data['message']
        if data['image1']:
            file_data1 = base64.b64decode(data['image1'])
            file_name1 = "temp_files/" + str(time.time_ns()) + '.png'
            with open(file_name1, 'wb') as f:
                f.write(file_data1)
        else:
            file_name1 = None
        if data['image2']:
            file_data2 = base64.b64decode(data['image2'])
            file_name2 = "temp_files/" + str(time.time_ns()) + '.png'
            with open(file_name2, 'wb') as f:
                f.write(file_data2)
        else:
            file_name2 = None
        return {'message': message, 'file_name1': file_name1, 'file_name2': file_name2}
    return None


def get_action_code(message):
    params = {'message': message}
    response = requests.get(JAVA_BACKEND + "/user-action", params=params)
    if response.status_code // 100 == 2:
        data = response.text
        return data
    return None


def get_law_update():
    response = requests.get(JAVA_BACKEND + "/law-update")
    if response.status_code // 100 == 2:
        if response.text == "No updates in law":
            return None
        return response.text
    return None


def post_remainings(file_path):
    files = {'file': open(file_path, 'rb')}
    response = requests.post(JAVA_BACKEND + "/upload/remainings", files=files)
    if response.status_code // 100 == 2:
        os.remove(file_path)
        return 'Файл успешно загружен.'
    else:
        return 'Ошибка при загрузке файла, попробуйте еще раз.'


def post_turnovers(file_path):
    files = {'file': open(file_path, 'rb')}
    response = requests.post(JAVA_BACKEND + "/upload/turnovers", files=files)
    if response.status_code // 100 == 2:
        os.remove(file_path)
        return 'Файл успешно загружен.'
    else:
        os.remove(file_path)
        return 'Ошибка при загрузке файла, попробуйте еще раз.'


def get_json(product, id_user, predict, start_data, end_date):
    params = {'product': product, "id_user": id_user, "predict": predict, "start_date": start_data, "end_date": end_date}
    response = requests.get(JAVA_BACKEND + "/get-json", params=params)
    if response.status_code // 100 == 2:
        data = response.json()["mp"]
        return data
    return None