# jackson watcher bot

## Установка

Для начала необходимо установить rabbitmq:
```commandline
sudo apt install rabbitmq-server
```

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

## Запуск

Для инициализации БД запустить скрипт `python init.py`

Затем запустить воркеры Celery:
```commandline
celery -A jackson.worker worker -n worker@pc --detach
celery -A jackson.worker beat --detach
```

И, наконец, запуск бота - `python -m jackson`