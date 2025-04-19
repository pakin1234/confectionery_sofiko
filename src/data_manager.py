import aiofiles
import json
import os
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import date
from hashlib import sha256
import time


ORDERS_FILE = "../data/orders.json"
PRODUCTS_FILE = "../data/products.json"
COURSES_FILE = "../data/courses.json"

'''АРТЁМ: поменял атрибуты класса'''
class Course(BaseModel):
    item: str
    type: str
    description: str
    price: int
    image_url: str = None  # Новое поле для URL изображения

class Product(BaseModel):
    item: str
    type: str
    price: int

class Order(BaseModel):
    order_id: int
    item: str
    type: str
    price: int
    paid: bool
    date: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class DataManager:
    def __init__(self, orders_file_path: str = ORDERS_FILE, products_file_path: str = PRODUCTS_FILE, courses_file_path: str = COURSES_FILE):
        self.orders_file_path = orders_file_path
        self.products_file_path = products_file_path
        self.courses_file_path = courses_file_path
        self._products_data: List[Dict] = []
        self._courses_data: List[Course] = []  # Новое поле для кэширования курсов

    async def _load_products_initial(self) -> None:
        """Асинхронная загрузка данных из products.json."""
        if not os.path.exists(self.products_file_path):
            self._products_data = []
            return

        try:
            async with aiofiles.open(self.products_file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    self._products_data = []
                    return

                self._products_data = json.loads(content)
        except (json.JSONDecodeError, Exception):
            self._products_data = []

    async def load_products_base(self) -> List[Dict]:
        """Возвращает кэшированные данные."""
        if not self._products_data:
            await self._load_products_initial()
        return self._products_data

    async def reload_products(self) -> None:
        """Перезагружает данные из products.json."""
        await self._load_products_initial()

    '''ПАША: Закомментировал код Влада, так как не получалось подгрузить данные'''
    # async def load_products_base(self) -> List[Dict]:
    #     # ПАША: возвращает просто список, надо исправить docstring
    #     ''' 
    #     Получаем всю базу кондитерских изделий 
    #     возвращает значение типа: [Product(item='Торт Прага', type='product', price=300), ...]
    #     надо будет распарсить, когда будем состыковывать модули
    #     '''

    #     if not os.path.exists(self.products_file_path):
    #         return {}

    #     async with aiofiles.open(self.products_file_path, mode='r', encoding='utf-8') as f:
    #         content = await f.read()
    #         if not content.strip():
    #             return {}

    #         data = json.loads(content)
    #         # ПАША: исправил на просто возвращение списка для файла product.json с категориями
    #         return data

    async def _load_courses_initial(self) -> None:
        """Асинхронная загрузка данных из courses.json."""
        if not os.path.exists(self.courses_file_path):
            self._courses_data = []
            return

        try:
            async with aiofiles.open(self.courses_file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    self._courses_data = []
                    return

                data = json.loads(content)
                self._courses_data = [Course(**item) for item in data]
        except (json.JSONDecodeError, Exception):
            self._courses_data = []

    async def load_courses_base(self) -> List[Course]:
        """Возвращает кэшированные данные о курсах."""
        if not self._courses_data:
            await self._load_courses_initial()
        return self._courses_data

    async def reload_courses(self) -> None:
        """Перезагружает данные из courses.json."""
        await self._load_courses_initial()

    '''АРТЁМ: заккоментил владовский код, сделал такую же реализацию как у паши с кэшем'''

    # async def load_courses_base(self) -> List[Course]:
    #     '''
    #     Получаем всю базу курсов
    #     возвращает значение типа: [Course(item='Инфоцыганский курс 1',
    #     type='course', description='Научим печь cumдитерские изделия',
    #     schedule='8:40 - бегит; 9:00 - прес качат; 9:05 - анжуманя; 9:07 - турник; 10:00 - месить тесто',
    #     price=300), ...]
    #     надо будет распарсить, когда будем состыковывать модули
    #     '''
    #
    #     if not os.path.exists(self.courses_file_path):
    #         return {}
    #
    #     async with aiofiles.open(self.courses_file_path, mode='r', encoding='utf-8') as f:
    #         content = await f.read()
    #         if not content.strip():
    #             return {}
    #
    #         data = json.loads(content)
    #
    #         return [Course(**item) for item in data]

    async def load_orders_base(self) -> Dict[str, List[Order]]:
        ''' Получаем всю базу заказов '''

        if not os.path.exists(self.orders_file_path):
            return {}

        async with aiofiles.open(self.orders_file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            if not content.strip():
                return {}

            raw_data = json.loads(content)
            return {
                user_id: [Order(**order) for order in orders]
                for user_id, orders in raw_data.items()
            }

    async def save_all_data(self, data: Dict[str, List[Order]]):
        ''' Сохраняем всю базу заказов '''

        async with aiofiles.open(self.orders_file_path, mode='w', encoding='utf-8') as f:
            serializable_data = {
                user_id: [order.model_dump() for order in orders]
                for user_id, orders in data.items()
            }
            await f.write(json.dumps(serializable_data, indent=4, ensure_ascii=False))

    async def add_order(self, user_id: int, order_data: dict) -> Order:
        ''' Добавляем заказ в базу '''
        user_id_str = str(user_id)
        data = await self.load_orders_base()
        order_list = data.get(user_id_str, [])

        next_order_id = (
            max((order.order_id for order in order_list), default=0) + 1
        )
        order = Order(order_id=next_order_id, **order_data)
        order_list.append(order)
        data[user_id_str] = order_list

        await self.save_all_data(data)
        return order

    async def get_orders(self, user_id: int) -> List[Order]:
        ''' Получаем список заказов от определенного пользователя. Нужно чтобы посмотреть неоплаченные заказы '''
        data = await self.load_orders_base()
        return data.get(str(user_id), [])
    
    async def check_not_paid(self, user_id: int):
        ''' Смотрим неоплаченные заказы. Когда будем состыковывать можно будет изменить print на return '''
        user_orders = await self.get_orders(user_id)
        for order in user_orders:
            if (not order.paid):
                print(f"Ваш заказ '{order.item}' на сумму '{order.price}$' еще не оплачен")
    
    async def get_product_from_base(self, item: str):
        ''' Получаем изделие по имени из базы, возвращаем данные в формате словаря. Нужно для того, чтобы передать словарь в параметры функции добавления заказа, 
        или для вывода информации о заказе клиенту(если это будем делать)'''
        product_base = await self.load_products_base()
        for product in product_base:
            if product.item == item:
                today = date.today().isoformat()
                order_data = {
                "item": product.item,
                "type": product.type,
                "price": product.price,
                "paid": False,
                "date": today
                }
                return order_data
    
    async def get_course_from_base(self, item: str):
        ''' Получаем курс по имени из базы, возвращаем данные в формате словаря. Нужно для того, чтобы передать словарь в параметры функции добавления заказа, 
        или для вывода информации о заказе клиенту(если это будем делать)'''
        courses_base = await self.load_courses_base()
        for course in courses_base:
            if course.item == item:
                today = date.today().isoformat()
                order_data = {
                "item": course.item,
                "type": course.type,
                "price": course.price,
                "paid": False,
                "date": today
                }
                return order_data
        




# async def main():
#     manager = DataManager()

#     ''' Когда будем вызывать какие-то функции работы с базами, которые принимают тг-id пользователя 
#     лучше использовать sha256 от id в качестве параметра id,
#     и выглядеть это должно так: sha256(message.from_user.id).hexdigest()'''

#     # Добавляем заказ
#     item = input("введите изделие: ")
#     new_order = await manager.add_order(
#         user_id=sha256("tg-id".encode('utf-8')).hexdigest(),
#         order_data = await manager.get_product_from_base(item))
#     print(new_order)


#     # Смотрим неоплаченные
    
#     await manager.check_not_paid(sha256("tg-id".encode('utf-8')).hexdigest())


# asyncio.run(main())