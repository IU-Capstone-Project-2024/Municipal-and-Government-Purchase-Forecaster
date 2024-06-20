FROM python:3.8-slim-bullseye
COPY . /aiogram_bot
WORKDIR ./aiogram_bot
RUN mkdir temp_files
RUN pip install -r bot_requirements.txt
CMD ["python", "bot.py"]