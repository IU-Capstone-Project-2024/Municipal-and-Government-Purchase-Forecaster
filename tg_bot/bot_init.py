import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

load_dotenv("./tg_conf.env")

BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
