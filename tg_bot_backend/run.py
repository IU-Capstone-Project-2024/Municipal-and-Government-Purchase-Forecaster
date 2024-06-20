from os import getenv
from dotenv import load_dotenv

from app import create_app

# Load environment variables from .env file
load_dotenv(dotenv_path="tg_back_conf.env")

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
