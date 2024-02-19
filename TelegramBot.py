import atexit
import tomllib
import logging
import psutil
import time
# import concurrent.futures
import threading
from pathlib import Path
from typing import Any

import telebot
from telebot import types

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

with open("config.toml", 'rb') as f_in:
    config: dict[str, Any] = tomllib.load(f_in)

# Start a bot instance
bot = telebot.TeleBot(config['TOKEN'])
USERS_LIST: Path = Path("users_list.txt")
users: set[int]
if USERS_LIST.exists():
    with open(USERS_LIST, "rt") as f_in:
        users = set(map(int, f_in.readlines()))
else:
    users = set()


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton("/start")
    markup.add(btn1)
    bot.send_message(message.from_user.id, "Monitoring started!", reply_markup=markup)
    users.add(message.from_user.id)


def send_startup_message():
    for userid in users:
        try:
            bot.send_message(chat_id=userid, text='⚠️ Computer has been started up.')
        except Exception as e:
            logging.error(f'Error while sending startup message: {e}')


def send_shutdown_message():
    for userid in users:
        try:
            bot.send_message(chat_id=userid, text='⚠️ Computer has been shut down.')
        except Exception as e:
            logging.error(f'Error while sending shutdown message: {e}')

    with open(USERS_LIST, 'wt') as f_out:
        f_out.writelines(f'{user}\n' for user in users)


def check_process(process_name):
    """
    Check if there is any running process that contains the given name processName.
    """
    # Iterate over the all the running process
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if process_name.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def proc_status(process_name):
    # TODO: loop breaking
    try:
        while True:
            # Check if process was running or not.
            if check_process(process_name):
                for userid in users:
                    try:
                        bot.send_message(chat_id=userid, text='Requested process was running')
                        time.sleep(5)
                    except Exception as e:
                        logging.error(f'Error while sending process status message: {e}')
            else:
                for userid in users:
                    try:
                        bot.send_message(chat_id=userid, text='No requested process was running')
                        time.sleep(5)
                    except Exception as e:
                        logging.error(f'Error while sending process status message: {e}')
    except KeyboardInterrupt:
        for userid in users:
            try:
                bot.send_message(chat_id=userid, text='Requested process checking interrupted')
            except Exception as e:
                logging.error(f'Error while sending process status message: {e}')


send_startup_message()

# with concurrent.futures.ThreadPoolExecutor() as executor:
#     futures = [executor.submit(bot.polling(interval=0)), executor.submit(proc_status, 'chrome')]
#     concurrent.futures.wait(futures)

thread_one = threading.Thread(target=bot.polling(non_stop=True, interval=0))
thread_two = threading.Thread(target=proc_status('REQUESTED_PROCESS_HERE'))

# Start threads
thread_one.start()
thread_two.start()

# TODO: for some reason thread_two doesn't start concurrently

# Register the send_shutdown_message function to be executed when the program exits
atexit.register(send_shutdown_message)
