import atexit
import logging
import tomllib
from contextlib import suppress
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Any

import psutil
from telebot import types, apihelper, TeleBot

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger: logging.Logger = logging.getLogger(Path(__file__).stem)

with open("config.toml", 'rb') as f_in:
    config: dict[str, Any] = tomllib.load(f_in)

# Start a bot instance
bot = TeleBot(config['TOKEN'])

PROCESS_NAME: str = config['procName']
USERS_LIST: Path = Path(config['usersList'])
users: set[int]
if USERS_LIST.exists():
    with open(USERS_LIST, "rt") as f_in:
        users = set(map(int, f_in.readlines()))
else:
    users = set()


@bot.message_handler(commands=['start'])
def start(message) -> None:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("/start"))
    user: int = message.from_user.id
    bot.send_message(user, "Monitoring started!", reply_markup=markup)
    users.add(user)
    logger.info(f'User {user} joined')


def send_startup_message() -> None:
    for userid in users.copy():
        try:
            bot.send_message(chat_id=userid, text='⚠️ Computer has been started up.')
        except apihelper.ApiTelegramException as ex:
            if ex.error_code == 403:
                users.discard(userid)
                logger.info(f'Error while sending startup message: {ex}')
            else:
                logger.error(f'Error while sending startup message: {ex}')
        except Exception as ex:
            logger.error(f'{type(ex)} while sending startup message: {ex}')


def send_shutdown_message() -> None:
    for userid in users.copy():
        try:
            bot.send_message(chat_id=userid, text='⚠️ Computer has been shut down.')
        except apihelper.ApiTelegramException as ex:
            if ex.error_code == 403:
                users.discard(userid)
                logger.info(f'Error while sending shutdown message: {ex}')
            else:
                logger.error(f'Error while sending shutdown message: {ex}')
        except Exception as ex:
            logger.error(f'{type(ex)} while sending shutdown message: {ex}')

    with open(USERS_LIST, 'wt') as f_out:
        f_out.writelines(f'{user}\n' for user in users)


def check_process(process_name: str) -> bool:
    """
    Check if there is any running process that contains the given name processName.
    """
    process_name = process_name.casefold()
    # Iterate over the all the running process
    for proc in psutil.process_iter():
        with suppress(psutil.Error):
            # Check if process name contains the given name string.
            if process_name in proc.name().casefold():
                return True
    return False


def proc_status(process_name: str) -> None:
    """
    Check if process was running or not.
    """

    is_running: bool
    was_running: bool = check_process(process_name)
    text: str
    while True:
        is_running = check_process(process_name)
        if not was_running and is_running:
            text = f'`{process_name}` has started'
        elif was_running and not is_running:
            text = f'`{process_name}` has ended'
        else:
            text = ''
        if text:
            for userid in users.copy():
                try:
                    bot.send_message(chat_id=userid, text=text, parse_mode='MarkdownV2')
                    logger.info(text)
                except apihelper.ApiTelegramException as ex:
                    if ex.error_code == 403:
                        users.discard(userid)
                        logger.info(f'Error while sending process status message: {ex}')
                    else:
                        logger.error(f'Error while sending process status message: {ex}')
                except Exception as ex:
                    logger.error(f'{type(ex)} while sending process status message: {ex}')
        was_running = is_running
        sleep(5)


def main() -> None:
    send_startup_message()

    process_checker: Thread = Thread(target=proc_status, args=(PROCESS_NAME,), daemon=True)

    # Start threads
    process_checker.start()
    bot.polling(non_stop=True, interval=0)


if __name__ == '__main__':
    # Register the send_shutdown_message function to be executed when the program exits
    atexit.register(send_shutdown_message)

    main()
