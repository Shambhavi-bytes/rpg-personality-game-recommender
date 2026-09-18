import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-later")
    DEBUG = False
    RECOMMENDATION_COUNT = 5
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class DevelopmentConfig(Config):
    DEBUG = True