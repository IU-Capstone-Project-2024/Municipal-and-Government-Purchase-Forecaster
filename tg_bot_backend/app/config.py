from os import getenv
from dotenv import load_dotenv

load_dotenv(dotenv_path="../tg_back_conf.env")

class Config:
    KEYCLOAK_URL = getenv("KEYCLOAK_URL")
    CLIENT_ID = getenv("CLIENT_ID")
    REALM_NAME = getenv("REALM_NAME")
    CLIENT_SECRET_KEY = getenv("CLIENT_SECRET_KEY")
    AUTHORIZATION_TOKEN = getenv("AUTH_BACK_TOKEN")
