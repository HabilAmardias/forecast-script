import psycopg2
from dotenv import load_dotenv
from os import getenv

load_dotenv()


class Config():
    def __init__(self):
        self.db = psycopg2.connect(
            database=getenv("POSTGRES_DB"),
            user=getenv("POSTGRES_USER"),
            password=getenv("POSTGRES_PASSWORD"),
            host=getenv("DATABASE_HOST"),
            port=getenv("DATABASE_PORT")
        )


def create_new_config() -> Config:
    return Config()