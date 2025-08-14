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
user_active_mask = {
    # 'user_id':"emoji"
}

MASKS = [
    {'id': 'mask1', 'price': 5, 'emoji': '🇺🇦', 'name': 'Ukraine'},
    {'id': 'mask2', 'price': 100, 'emoji': '🗼', 'name': 'Eiffel Tower'},
    {'id': 'mask3', 'price': 20, 'emoji': '♟', 'name': 'Chess Pawn'},
    {'id': 'mask4', 'price': 90, 'emoji': '🗽', 'name': 'Statue of Liberty'},
    {'id': 'mask5', 'price': 10, 'emoji': '⚜️', 'name': 'Fleur-de-lis'},
    {'id': 'mask6', 'price': 45, 'emoji': '🦠', 'name': 'Virus'},
    {'id': 'mask7', 'price': 60, 'emoji': '⛱', 'name': 'Beach Umbrella'},
    {'id': 'mask8', 'price': 30, 'emoji': '🎭', 'name': 'Theatre Mask'},
    {'id': 'mask9', 'price': 25, 'emoji': '👺', 'name': 'Tengu Mask'},
    {'id': 'mask10', 'price': 70, 'emoji': '🤖', 'name': 'Robot'},
    {'id': 'mask11', 'price': 15, 'emoji': '😷', 'name': 'Medical Mask'},
    {'id': 'mask12', 'price': 35, 'emoji': '🎃', 'name': 'Pumpkin'},
    {'id': 'mask13', 'price': 55, 'emoji': '👹', 'name': 'Oni Mask'},
    {'id': 'mask14', 'price': 80, 'emoji': '👽', 'name': 'Alien'},
    {'id': 'mask15', 'price': 95, 'emoji': '🤑', 'name': 'Money Face'},
    {'id': 'mask16', 'price': 40, 'emoji': '🧛', 'name': 'Vampire'},
    {'id': 'mask17', 'price': 85, 'emoji': '🦸', 'name': 'Superhero'},
    {'id': 'mask18', 'price': 65, 'emoji': '🧙', 'name': 'Wizard'},
    {'id': 'mask19', 'price': 75, 'emoji': '🧞', 'name': 'Genie'},
    {'id': 'mask20', 'price': 50, 'emoji': '👻', 'name': 'Ghost'}
]
BOOSTS = [
    {"id": "boost1", "name": "Speed 30m", "time": 30, "price": 5},  # 30 мин
    {"id": "boost2", "name": "Speed 1h", "time": 60, "price": 10},  # 1 час
    {"id": "boost3", "name": "Speed 2h", "time": 120, "price": 20},  # 2 часа
    {"id": "boost4", "name": "Speed 4h", "time": 240, "price": 40},  # 4 часа
    {"id": "boost5", "name": "Speed 6h", "time": 360, "price": 60},  # 6 часов
    {"id": "boost6", "name": "Speed 8h", "time": 480, "price": 80},  # 8 часов
    {"id": "boost7", "name": "Speed 10h", "time": 600, "price": 100},  # 10 часов
    {"id": "boost8", "name": "Speed 12h", "time": 720, "price": 120},  # 12 часов
]
