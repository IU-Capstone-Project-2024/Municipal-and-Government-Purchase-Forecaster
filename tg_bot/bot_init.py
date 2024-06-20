from os import getenv

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

load_dotenv(dotenv_path="../tg_conf.env")

bot = Bot(token=getenv('BOT_TOKEN'))
dp = Dispatcher()
