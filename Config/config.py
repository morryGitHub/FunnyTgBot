from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    # payment_token: str


@dataclass
class DatabaseConfig:
    database: str  # Название базы данных
    db_host: str  # URL-адрес базы данных
    db_port: int  # порт
    db_user: str  # Username пользователя базы данных
    db_password: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig


def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env(path=path)

    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            admin_ids=list(map(int, env.list('ADMIN_IDS'))),
            # payment_token=env("PAYMENTS_TOKEN")
        ),
        db=DatabaseConfig(
            database=env('MYSQLDATABASE'),
            db_host=env('MYSQLHOST'),
            db_port=env.int('MYSQLPORT'),
            db_user=env('MYSQLUSER'),
            db_password=env('MYSQLPASSWORD')
        )
    )
