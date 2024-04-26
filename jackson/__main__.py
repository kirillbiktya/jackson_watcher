from jackson.telegram_bot import bot
from jackson.database import engine, models


models.Base.metadata.create_all(bind=engine)

bot.polling(non_stop=True)
