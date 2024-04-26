import celery
from config import DB_URL
from jackson.database import SessionLocal
from jackson.database.models import Ticker, User
from jackson.cmc_api import CMCAPI
from jackson.telegram_bot import bot
from jackson.utils import row2dict
from datetime import timedelta, datetime


celery_app = celery.Celery('jackson_telegram_bot', broker='pyamqp://guest@localhost//', backend='db+' + DB_URL)

celery_app.conf.beat_schedule = {
    'ticker_price_collector': {
        'task': 'jackson.worker.ticker_price_collector',
        'schedule': 60.0
    }
}

cmc_client = CMCAPI()
db = SessionLocal()


@celery_app.task
def ticker_price_collector():
    tickers = db.query(Ticker).all()
    if len(tickers) == 0:
        return

    coin_ids = list(set([str(x.cmc_coin_id) for x in tickers]))
    coins_prices = cmc_client.get_coins_price(coin_ids)

    users = db.query(User).all()
    for user in users:
        for ticker in user.tickers:
            celery_app.send_task(
                "jackson.worker.notify_user",
                args=[user.telegram_id, row2dict(ticker), coins_prices[str(ticker.cmc_coin_id)]["quote"]["USD"]["price"]]
            )


@celery_app.task
def notify_user(user_id: int, ticker: dict, price: float):
    if ticker["latest_notify"] is not None:
        if ticker["latest_notify"] - timedelta(minutes=5) < datetime.now():
            return

    if ticker["floor_value"] > price:
        bot.send_message(user_id, "Цена на {} упала - текущий курс ${}".format(ticker["name"], price))
        db.query(Ticker).filter(Ticker.id == ticker["id"]).update({"latest_notify": datetime.now()})
        db.commit()
    elif ticker["ceil_value"] < price:
        bot.send_message(user_id, "Цена на {} выросла - текущий курс ${}".format(ticker["name"], price))
        db.query(Ticker).filter(Ticker.id == ticker["id"]).update({"latest_notify": datetime.now()})
        db.commit()
    else:
        return

    return
