# jackson watcher bot

## Установка

Для начала необходимо установить rabbitmq:
```commandline
sudo apt install rabbitmq-server python3-venv
```

> [!NOTE]
> Работать лучше в скрине или tmux, так бот не отвалится, если завершить сессию

Склонировать репозиторий
```commandline
git clone https://github.com/kirillbiktya/jackson_watcher
```

Создать виртуальное окружение и установить зависимости:
```commandline
cd jackson_watcher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Переименуйте файл `config_template.py` и внесите в него действительные ключи для доступа к API Telegram и Coinmarketcap
```commandline
mv config_template.py config.py
nano config.py
```

## Запуск

Для инициализации БД запустить скрипт `python init.py`

Затем запустить воркеры Celery:
```commandline
celery -A jackson.worker worker -n worker@pc --detach
celery -A jackson.worker beat --detach
```

И, наконец, запуск бота - `python -m jackson`

## Использование (Telegram)

Команды:
- /start - Начало работы с ботом (на данном этапе бот заносит пользователя в БД, 
  так что использование данной команды при начале работы с ботом обязательно)
- /new_ticker - Создание нового тикера (отслеживания курса коина)
- /my_tickers - Список тикеров пользователя

По мере изменения цены на коин бот будет присылать уведомления. 
Единственное ограничение в работе - обновление курса раз в минуту.
Что бы уведомления не сыпались каждую минуту, сделана задержка о повторном 
изменении цены (5 минут)
