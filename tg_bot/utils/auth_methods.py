import requests
import os
from dotenv import load_dotenv

load_dotenv("./tg_conf.env")

AUTH_BACK_TOKEN = os.getenv('AUTH_BACK_TOKEN')
KEYCLOAK_CALLBACK_URL = os.getenv('KEYCLOAK_CALLBACK_URL')

headers = {'Authorization': AUTH_BACK_TOKEN}


def get_token(user_id):
    response = requests.get(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id), headers=headers)
    if response.status_code == 200:
        return response.json()
    return None


def store_session(user_id, state):
    requests.post(KEYCLOAK_CALLBACK_URL + "store-session", headers=headers, json={'user_id': user_id, 'state': state})


def delete_token(user_id):
    requests.delete(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id), headers=headers)


def is_token_expired(user_id):
    response = requests.get(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id) + "/expired", headers=headers)
    if response.status_code == 200:
        return response.json()['expired']
    return False


def is_refresh_expired(user_id):
    response = requests.get(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id) + "/refresh-token-expired", headers=headers)
    if response.status_code == 200:
        return response.json()['expired']
    return False


def refresh_token(user_id):
    requests.post(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id) + "/refresh", headers=headers)


def get_user_ids():
    response = requests.get(KEYCLOAK_CALLBACK_URL + "get-userids", headers=headers)
    if response.status_code == 200:
        return response.json()['id_list']
    return None


def get_roles(user_id):
    response = requests.get(KEYCLOAK_CALLBACK_URL + "token/" + str(user_id) + "/roles", headers=headers)
    if response.status_code == 200:
        return response.json()['roles']
    return None
