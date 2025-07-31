# TABLE STATS
SELECT_SCORE_FROM_STATS = """
    SELECT score, last_used FROM Stats WHERE user_id = %s
"""

SELECT_ALL_SCORES = """
    SELECT Users.username, Stats.score
    FROM Stats
    JOIN Users ON Stats.user_id = Users.user_id
    ORDER BY Stats.score DESC
    
"""
# LIMIT 10;

SELECT_TIMES_FROM_STATS = """
    SELECT last_used, dice_control FROM Stats WHERE user_id = %s
"""

SELECT_COIN_FROM_STATS = """
    SELECT coin FROM Stats WHERE user_id = %s
"""

SELECT_ALL_SCORES_FROM_CHAT = """
    SELECT U.username, S.score
    FROM Stats S
    JOIN Users U ON S.user_id = U.user_id
    JOIN UsersChats C ON C.user_id = U.user_id
    WHERE C.chat_id = %s
    ORDER BY S.score DESC

"""

SELECT_COIN_FROM_STATS = """
    SELECT coin FROM Stats WHERE user_id = %s
"""

UPDATE_STATS_SCORE_TIME = """
    UPDATE Stats SET score = %s, last_used = %s WHERE user_id = %s
"""

UPDATE_STATS_COIN = """
    UPDATE Stats SET coin = %s WHERE user_id = %s
"""

UPDATE_AFTER_DICE = """
    UPDATE Stats 
    SET last_used = %s,
    coin = %s,
    dice_control = %s 
    WHERE user_id = %s
"""

INSERT_USER_INTO_STATS = """
    INSERT INTO Stats(user_id, score,last_used, coin, dice_control) VALUES (%s, %s,%s, %s, %s)
"""

# TABLE USERS
INSERT_USER_INTO_USERS = """
    INSERT INTO Users (user_id, username, active) VALUES (%s, %s, %s)
"""

'''UsersChats'''
INSERT_USER_INTO_UsersChats = """
    INSERT INTO UsersChats (user_id, chat_id) VALUES (%s, %s)
"""

CHECK_USER_CHAT_EXISTS = """
    SELECT EXISTS(SELECT 1 FROM UsersChats WHERE user_id = %s AND chat_id = %s)
"""
