import telebot
from config import TELEGRAM_API_KEY
from jackson.cmc_api import CMCAPI
from jackson.database import SessionLocal
from jackson.database.models import User, Ticker
from jackson.utils import inline_kb_constructor
import re
import base64


bot = telebot.TeleBot(TELEGRAM_API_KEY)
cmc = CMCAPI()

ticker_draft = {}


@bot.message_handler(commands=["start"])
def _start(message: telebot.types.Message):
    db = SessionLocal()
    try:
        db.add(User(telegram_id=message.from_user.id))
        db.commit()
    except Exception:  # TODO
        db.rollback()

    bot.send_message(
        message.chat.id,
        "Привет, {}! Используй команды:\n"
        "/new_ticker - добавить тикер для отслеживания\n"
        "/my_tickers - для управления существующими тикерами".format(message.from_user.first_name)
    )


@bot.message_handler(commands=["new_ticker"])
def _new_ticker(message: telebot.types.Message):
    coins = cmc.get_top10_coins()
    data = [{
        "text": x["name"],
        "callback_data": "new_ticker.{}".format(
            base64.b64encode("{}.{}".format(x["id"], x["name"]).encode("utf-8")).decode("utf-8")
        )
    } for x in coins]
    kb = inline_kb_constructor(data)
    bot.send_message(message.chat.id, "Выбери коин:", reply_markup=kb)


def _new_ticker_step1(message: telebot.types.Message):
    if not re.match(r"[0-9]+?[.,][0-9]+", message.text):
        m = bot.send_message(message.chat.id,
                             "Формат ввода - число с плавающей точкой (10,3245 или 43.345). Попробуй еще.")
        bot.register_next_step_handler(m, _new_ticker_step1)

    floor_value = float(message.text)
    ticker_draft[str(message.from_user.id)].update({"floor_value": floor_value})

    m = bot.send_message(message.chat.id, "Какая верхняя граница курса?")
    bot.register_next_step_handler(m, _new_ticker_step2)


def _new_ticker_step2(message: telebot.types.Message):
    if not re.match(r"[0-9]+?[.,][0-9]+", message.text):
        m = bot.send_message(message.chat.id,
                             "Формат ввода - число с плавающей точкой (10,3245 или 43.345). Попробуй еще.")
        bot.register_next_step_handler(m, _new_ticker_step2)

    ceil_value = float(message.text)
    ticker_draft[str(message.from_user.id)].update({"ceil_value": ceil_value})

    db = SessionLocal()
    db.add(Ticker(**ticker_draft[str(message.from_user.id)], owner_id=message.from_user.id))
    db.commit()

    bot.send_message(message.chat.id, "Окей! Добавил тикер на {} с границами ${} - ${}".format(
        ticker_draft[str(message.from_user.id)]["name"],
        ticker_draft[str(message.from_user.id)]["floor_value"],
        ticker_draft[str(message.from_user.id)]["ceil_value"]
    ))

    del ticker_draft[str(message.from_user.id)]


@bot.message_handler(commands=["my_tickers"])
def _my_tickers(message: telebot.types.Message):
    db = SessionLocal()
    user_tickers = db.query(Ticker).filter(Ticker.owner_id == message.from_user.id).all()
    if len(user_tickers) == 0:
        bot.send_message(message.chat.id, "У тебя нет тикеров!")
        return

    data = [{
        "text": "{}, ${}-${}".format(x.name, x.floor_value, x.ceil_value),
        "callback_data": "my_tickers.select.{}".format(x.id)
    } for x in user_tickers]

    kb = inline_kb_constructor(data, cols=1)
    bot.send_message(message.chat.id, "Твои активные тикеры:", reply_markup=kb)


@bot.callback_query_handler(lambda call: call.data.startswith("new_ticker"))
def _new_ticker_handler(callback: telebot.types.CallbackQuery):
    data = base64.b64decode(callback.data.split(".")[1]).decode("utf-8")
    cmc_coin_id = data.split(".")[0]
    name = data.split(".")[1]
    ticker_draft.update({str(callback.from_user.id): {"cmc_coin_id": cmc_coin_id, "name": name}})
    bot.edit_message_text("Выбран {}".format(name), callback.message.chat.id, callback.message.id)
    m = bot.send_message(callback.message.chat.id, "Какая нижняя граница для курса?")
    bot.register_next_step_handler(m, _new_ticker_step1)


@bot.callback_query_handler(lambda call: call.data.startswith("my_tickers"))
def _my_tickers_handler(callback: telebot.types.CallbackQuery):
    db = SessionLocal()
    operation = callback.data.split(".")[1]
    if operation == "back":
        user_tickers = db.query(Ticker).filter(Ticker.owner_id == callback.from_user.id).all()
        if len(user_tickers) == 0:
            bot.edit_message_text("У тебя нет тикеров!", callback.message.chat.id, callback.message.id,
                                  reply_markup=None)
            return
        data = [{
            "text": "{}, ${}-${}".format(x.name, x.floor_value, x.ceil_value),
            "callback_data": "my_tickers.select.{}".format(x.id)
        } for x in user_tickers]

        kb = inline_kb_constructor(data, cols=1)
        bot.edit_message_text("Твои активные тикеры:", callback.message.chat.id, callback.message.id,
                              reply_markup=kb)
    elif operation == "select":
        ticker_id = callback.data.split(".")[2]
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        if ticker is None:
            bot.edit_message_text("Ошибка!", callback.message.chat.id, callback.message.id, reply_markup=None)
            return

        kb = inline_kb_constructor([{"text": "Удалить", "callback_data": "my_tickers.delete.{}".format(ticker_id)},
                                    {"text": "Назад", "callback_data": "my_tickers.back"}])
        bot.edit_message_text("Тикер на {}\n${} - ${}".format(ticker.name, ticker.floor_value, ticker.ceil_value),
                              callback.message.chat.id, callback.message.id, reply_markup=kb)
        return
    elif operation == "delete":
        ticker_id = callback.data.split(".")[2]
        ticker = db.query(Ticker).filter(Ticker.id == ticker_id).first()
        if ticker is None:
            bot.edit_message_text("Ошибка!", callback.message.chat.id, callback.message.id, reply_markup=None)
            return

        db.delete(ticker)
        db.commit()

        bot.edit_message_text("Тикер удален!", callback.message.chat.id, callback.message.id, reply_markup=None)
        user_tickers = db.query(Ticker).filter(Ticker.owner_id == callback.from_user.id).all()
        if len(user_tickers) == 0:
            bot.edit_message_text("У тебя нет тикеров!", callback.message.chat.id, callback.message.id,
                                  reply_markup=None)
            return
        data = [{
            "text": "{}, ${}-${}".format(x.name, x.floor_value, x.ceil_value),
            "callback_data": "my_tickers.select.{}".format(x.id)
        } for x in user_tickers]

        kb = inline_kb_constructor(data, cols=1)
        bot.edit_message_text("Твои активные тикеры:", callback.message.chat.id, callback.message.id,
                              reply_markup=kb)
        return
