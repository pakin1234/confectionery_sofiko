from environs import Env

def read_bot_token():
    env = Env()
    env.read_env()

    return env.str("BOT_TOKEN")