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
    # TODO: ticker management inline menu
    pass


@bot.callback_query_handler(lambda call: call.data.startswith("new_ticker"))
def _new_ticker_handler(callback: telebot.types.CallbackQuery):
    data = base64.b64decode(callback.data.split(".")[1]).decode("utf-8")
    cmc_coin_id = data.split(".")[0]
    name = data.split(".")[1]
    ticker_draft.update({str(callback.from_user.id): {"cmc_coin_id": cmc_coin_id, "name": name}})
    bot.edit_message_text("Выбран {}".format(name), callback.message.chat.id, callback.message.id)
    m = bot.send_message(callback.message.chat.id, "Какая нижняя граница для курсв?")
    bot.register_next_step_handler(m, _new_ticker_step1)

