import aiomysql

from Config.config import load_config, Config

db_config: Config = load_config(".env")


async def create_pool():
    pool = await aiomysql.create_pool(
        host=db_config.db.db_host,
        port=db_config.db.db_port,
        user=db_config.db.db_user,
        password=db_config.db.db_password,
        db=db_config.db.database,
        minsize=1,
        maxsize=2,
        connect_timeout=10,
        autocommit=True
    )
    return pool


async def close_pool(db_pool):
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()


user_chat_messages = {}

masks = {
    1: "⚜️",
    2: "🗼",
    3: "♟",
    4: "🗽",
    5: "🇺🇦",
    6: "🦠",
    7: "⛱",
}
