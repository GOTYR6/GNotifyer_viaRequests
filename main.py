import requests
import requests.cookies
import requests.utils
import json
from threading import Event
from configuration import config
from tqdm import tqdm
import time
import datetime
from datetime import datetime as dt
import telebot
from telebot import types
import os
from random import randrange
import tempfile
from PIL import ImageGrab

event = Event()
event.set()
bot = telebot.TeleBot(config.TOKEN)


def get_chat_id():
    url = f"https://api.telegram.org/bot{config.TOKEN}/getUpdates"
    print(requests.get(url).json())


def get_authorized():
    session = requests.Session()
    payload = {'login': config.LOGIN, 'password': config.PASSWORD}
    session.headers['user-Agent'] = config.USER_AGENT
    session.post(config.AUTH_PAGE, json=payload)
    response = session.get(config.TASKS_PAGE.format(0))
    if response.status_code == 200:
        if not os.path.exists("data/"):
            os.mkdir("data/")
        with open(config.COOKIES, 'w') as file:
            json.dump(requests.utils.dict_from_cookiejar(session.cookies), file)
        print("Successfully logged in and created cookies!")
        return session
    else:
        print("Unsuccessful authorization attempt!")


def create_session():
    if os.path.exists(config.COOKIES):
        session = requests.Session()
        session.headers['user-Agent'] = config.USER_AGENT
        with open(config.COOKIES) as file:
            cookies = json.load(file)
            session.cookies.update(cookies)
            response = session.get(config.TASKS_PAGE.format(0))
            if response.status_code == 200:
                print('Existing cookies are used')
                return session
            else:
                print("Existing cookies doesn't work, will try to log in")
                session = get_authorized()
                return session
    else:
        print("Cookies wasn't found, will try to log in")
        session = get_authorized()
        return session


def get_correct_date(date: str) -> str:
    correct_date = dt.fromisoformat(date) + datetime.timedelta(hours=3)
    return correct_date.strftime("%d.%m.%Y %H:%M")


def get_tasks(session, exist_tasks_id):
    while True:
        tasks_data = dict()
        offset = 0
        response: dict = json.loads(session.get(config.TASKS_PAGE.format(offset)).text)
        tasks_quantity: int = response.get('totalCount')
        print(f'\nFound: {tasks_quantity} tasks')
        while offset < tasks_quantity:
            cur_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            tasks: list = response.get('data')
            for task in tqdm(tasks, desc=f'Parsing was started at {cur_time}', unit=' task'):
                task_id = task.get('Id')
                task_link = config.LINK.format(task_id)
                task_deadline = get_correct_date(task.get('PlannedCompletionDate'))  # '2023-05-17T10:00:00.0000000Z'
                tasks_data[task_id] = {'id': task_id, 'link': task_link, 'deadline': task_deadline}
            offset += 100
            response: dict = json.loads(session.get(config.TASKS_PAGE.format(offset)).text)
        if len(tasks_data) == tasks_quantity:
            break
        else:
            print('Not all tasks were found. Retry after 20 seconds')
            time.sleep(config.DRIVER_TIMEOUT)
            continue
    if exist_tasks_id:
        parsed_tasks_id = {task_id for task_id in tasks_data}
        new_tasks_id = parsed_tasks_id.difference(exist_tasks_id)
        if new_tasks_id:
            new_tasks_data = sorted([tasks_data.get(task_id) for task_id in new_tasks_id],
                                    key=lambda new_task: dt.strptime(new_task.get('deadline'), "%d.%m.%Y %H:%M"))
            return parsed_tasks_id, new_tasks_data
        else:
            return parsed_tasks_id, None
    else:
        parsed_tasks_id = {task_id for task_id in tasks_data}
        return parsed_tasks_id, None


def start_notifyer(timeout: int):
    exist_tasks_id = set()
    remind_time = time.time()
    session = create_session()
    bot.send_message(chat_id=config.CHAT_ID, text='Notifyer is running, you will be notified about new tasks asap👍')
    while not event.is_set():
        try:
            exist_tasks_id, new_tasks = get_tasks(session, exist_tasks_id)
            if new_tasks:
                print(f'Founded {len(new_tasks)} new tasks')
                message = f'Количество новых задач: {len(new_tasks)}\n'
                for index, task in enumerate(new_tasks, start=1):
                    message += f"{index}) [{task.get('id')}]({task.get('link')}) Крайний срок: {task.get('deadline')}\n"
                bot.send_message(chat_id=config.CHAT_ID, text=message, parse_mode='Markdown')
            if time.time() - remind_time > config.REMIND_TIMEOUT and not event.is_set():
                bot.send_message(chat_id=config.CHAT_ID, text='Notifyer is still in progress!')
                remind_time = time.time()
            event.wait(timeout + randrange(timeout))
        except KeyboardInterrupt:
            print('Parsing has been stopped')
        except (Exception,):
            continue
    bot.send_message(chat_id=config.CHAT_ID, text='Notifyer has been stopped⛔️')


@bot.message_handler(commands=['start'], func=lambda message: message.chat.id in config.ALLOW_CHAT_ID)
def welcome(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    startup = types.KeyboardButton('Start notifyer')
    shutdown = types.KeyboardButton('Shut down notifyer')
    screen = types.KeyboardButton('Take screenshot')
    turnoff = types.KeyboardButton('Turn off PC')
    markup.add(startup, shutdown, screen, turnoff)
    bot.send_message(message.chat.id, 'Welcome! How can I help you?👋', reply_markup=markup)


@bot.message_handler(regexp='Start notifyer', func=lambda message: message.chat.id in config.ALLOW_CHAT_ID)
def remote_startup(message: types.Message):
    if event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        event.clear()
        config.CHAT_ID = message.chat.id
        return start_notifyer(timeout=config.NOTIFYER_TIMEOUT)
    if not event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return bot.send_message(message.chat.id, 'Notifyer is already running!👌')


@bot.message_handler(regexp='Shut down notifyer', func=lambda message: message.chat.id in config.ALLOW_CHAT_ID)
def remote_shutdown(message: types.Message):
    if not event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return event.set()
    if event.is_set() and message.chat.id in config.ALLOW_CHAT_ID:
        return bot.send_message(message.chat.id, 'Notifyer is already has been stopped!✋')


@bot.message_handler(regexp='Take screenshot', func=lambda message: message.chat.id in config.ALLOW_CHAT_ID)
def screenshot(message: types.Message):
    path = tempfile.gettempdir() + 'screenshot.png'
    ImageGrab.grab().save(path, 'PNG')
    return bot.send_document(message.chat.id, open(path, 'rb'))


@bot.message_handler(regexp='Turn off PC', func=lambda message: message.chat.id in config.ALLOW_CHAT_ID)
def confirm_turnoff(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    confirm = types.InlineKeyboardButton('Yes', callback_data='confirm')
    decline = types.InlineKeyboardButton('No', callback_data='decline')
    markup.add(confirm, decline)
    if event.is_set():
        return bot.send_message(message.chat.id, 'Are you sure you want to turn off your PC?', reply_markup=markup)
    if not event.is_set():
        return bot.send_message(message.chat.id,
                                'Warning! Notifyer is still in progress, do you still want to turn off your PC?',
                                reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_inline(call):
    try:
        if call.message:
            if call.data == 'confirm':
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Turning off your PC🖥🔌', reply_markup=None)
                return os.system("shutdown -s -t 0")
            if call.data == 'decline':
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                return bot.answer_callback_query(call.id, 'You canceled the PC shutdown❌')
    except Exception as e:
        print(e)


if __name__ == "__main__":
    bot.infinity_polling()
