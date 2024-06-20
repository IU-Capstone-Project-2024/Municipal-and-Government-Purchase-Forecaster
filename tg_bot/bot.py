import asyncio
import logging
from datetime import datetime
from functools import partial

from os import getenv

import aiocron
import pytz

from bot_init import dp, bot
from handlers.base import base_router, send_news
from handlers.callbacks import callback_router
from handlers.messages import message_router
from utils.auth_methods import get_user_ids

# Set up logging
logging.basicConfig(level=logging.INFO)

dp.include_routers(base_router, message_router, callback_router)


async def main():
    timezone = pytz.timezone('Etc/GMT-3')
    send_news_partial = partial(send_news, bot_instance=bot)
    aiocron.crontab('0 11 * * *', func=send_news_partial, start=True, tz=timezone)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    asyncio.run(main())
