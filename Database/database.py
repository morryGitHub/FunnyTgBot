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

masks = [
    {'id': 'mask1', 'price': 5, 'emoji': '🇺🇦'},
    {'id': 'mask2', 'price': 100, 'emoji': '🗼'},
    {'id': 'mask3', 'price': 20, 'emoji': '♟'},
    {'id': 'mask4', 'price': 90, 'emoji': '🗽'},
    {'id': 'mask5', 'price': 10, 'emoji': '⚜️'},
    {'id': 'mask6', 'price': 45, 'emoji': '🦠'},
    {'id': 'mask7', 'price': 60, 'emoji': '⛱'},
    {'id': 'mask8', 'price': 30, 'emoji': '🎭'},
    {'id': 'mask9', 'price': 25, 'emoji': '👺'},
    {'id': 'mask10', 'price': 70, 'emoji': '🤖'},
    {'id': 'mask11', 'price': 15, 'emoji': '😷'},
    {'id': 'mask12', 'price': 35, 'emoji': '🎃'},
    {'id': 'mask13', 'price': 55, 'emoji': '👹'},
    {'id': 'mask14', 'price': 80, 'emoji': '👽'},
    {'id': 'mask15', 'price': 95, 'emoji': '🤑'},
    {'id': 'mask16', 'price': 40, 'emoji': '🧛'},
    {'id': 'mask17', 'price': 85, 'emoji': '🦸'},
    {'id': 'mask18', 'price': 65, 'emoji': '🧙'},
    {'id': 'mask19', 'price': 75, 'emoji': '🧞'},
    {'id': 'mask20', 'price': 50, 'emoji': '👻'}
]

