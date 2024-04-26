from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def inline_kb_constructor(buttons: list[dict], cols=3):
    """

    :param buttons: list of dicts like {"text": "...", "callback_data": "..."}
    :param cols:
    :return:
    """
    kb = InlineKeyboardMarkup()
    row = []
    for entry in buttons:
        row.append(InlineKeyboardButton(**entry))
        if len(row) == cols:
            kb.add(*row)
            row = []

    if len(row):
        kb.add(*row)

    return kb


def row2dict(row):
    d = {}
    for column in row.__table__.columns:
        d[column.name] = getattr(row, column.name)

    return d