# Кондитерская СофиКо


## Что будет делать бот
Бот должен выполнять три ключевые задачи:

1. Консультация по образовательным курсам: Предоставлять информацию о курсах (описание, расписание, цены).
2. Прием заказов: Позволять пользователям заказывать кондитерские изделия через удобный интерфейс.
3. Напоминание об оплате: Отслеживать статус оплаты заказов и отправлять напоминания, если оплата не произведена. 

## Примерная архитектура
### Логика работы бота
* Консультация по курсам:
1. Пользователь отправляет команду, например, /courses.
2. Бот читает courses.json и отправляет список курсов в виде сообщений (с кнопками для выбора, если используется aiogram).
*  Прием заказов:
1. Пользователь отправляет команду /order.
2. Бот предлагает меню (например, через инлайн-кнопки).
3. После выбора бот записывает заказ в orders.json, добавляя Telegram ID пользователя, название изделия, цену и статус оплаты (paid: false).
* Напоминание об оплате:
1. Бот периодически (например, раз в день) проверяет orders.json.
2. Если находит заказы с paid: false, отправляет пользователю сообщение: "Пожалуйста, оплатите заказ на сумму X рублей".


## Структура проекта и за что отвечают файлы
### Файл `requirements.txt`
Там все библиотеки, которые установлены, лучше использовать эти версии, если нужна доп библиотека, то либо обновите файл этот, либо просто напишите библиотеку и версию, чтобы добавить

### Папка data
1. Содержит json файлы для хранения своеобразной бд - будет убрана из гитхаба, так как личная информация, как пример пока пусть лежит
2. Файл `config.py` для чтения токена бота тг

### Папка reports
1. Файл exel с отчетами для заказчика

### Папка src:
1. Папка `handlers` - для различных хэндлеров для курсов, заказов и общие 
2. Файл `bot.py` - запуск бота и соединение всех хэндлеров
3. Файл `data_manager.py` - содержит все функции для работы с json файлам для чтения, записи и всего остального
4. Файл `excel_generator.py` - преобразование json файлов в excel файл
5. Файл `reminder.py` - для реализации отправки напоминаний и отслеживания оплаты



