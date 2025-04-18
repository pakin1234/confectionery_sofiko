from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from data_manager import DataManager
from handlers.common import get_main_menu_kb

data_manager = DataManager()
menu_router = Router()

class OrderStates(StatesGroup):
    choosing_item = State()
    entering_quantity = State()


async def get_category_kb() -> InlineKeyboardMarkup:
    products_data = await data_manager.load_products_base()
    builder = InlineKeyboardBuilder()
    for category in products_data:
        builder.button(text=category["name"], callback_data=category["category"])
    builder.adjust(1)
    return builder.as_markup()

async def get_item_kb(category_callback) -> InlineKeyboardMarkup:
    products_data = await data_manager.load_products_base()
    builder = InlineKeyboardBuilder()
    for category in products_data:
        if category["category"] == category_callback:
            for item in category["items"]:
                builder.button(text=item["item"], callback_data=item["callback_data"])
            break
    builder.adjust(2)
    return builder.as_markup()

async def get_quantity_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="1", callback_data="1")
    builder.button(text="2", callback_data="2")
    builder.button(text="3", callback_data="3")
    builder.button(text="4", callback_data="4")
    builder.button(text="5", callback_data="5")
    builder.adjust(1)
    return builder.as_markup()


@menu_router.message(F.text == "Товары")
@menu_router.message(Command(commands="order"))
async def start_order(message: Message, state: FSMContext):
    user_data = await state.get_data()
    if "cart" not in user_data:
        await state.update_data(cart=[])

    kb = await get_category_kb()
    await message.answer("Выберите категорию:", reply_markup=kb)
    await state.set_state(None)

@menu_router.callback_query(F.data.in_({"cupcake", "cake", "bouquet"}))
async def order_item(call: CallbackQuery,state: FSMContext):
    category = call.data
    await state.update_data(category=category)
    kb = await get_item_kb(category)
    await call.message.answer("Выберите, что вы хотите заказать", reply_markup=kb)
    await state.set_state(OrderStates.choosing_item)
    await call.answer()

@menu_router.callback_query(OrderStates.choosing_item)
async def select_item(call: CallbackQuery, state: FSMContext):
    item_callback = call.data
    products_data = await data_manager.load_products_base()
    item_data = None
    user_data = await state.get_data()
    category_data = user_data.get("category")

    kb = await get_quantity_kb()

    for categ in products_data:
        if categ["category"] == category_data:
            for item in categ["items"]:
                if item["callback_data"] == item_callback:
                    item_data = item
                    break
            break

    if not item_data:
        call.message.answer("Товар не найден")
        call.answer()
        return
    
    await state.update_data(item_data=item_data)
    await call.message.answer(f"Вы выбрали {item_data['item']}. Сколько Вы хотите заказать? (Введите число)", reply_markup=kb)
    await state.set_state(OrderStates.entering_quantity)
    await call.answer()

@menu_router.callback_query(OrderStates.entering_quantity, F.data.in_({"1", "2", "3", "4", "5"}))
async def enter_quantity(call: CallbackQuery, state: FSMContext):
    kb = await get_category_kb()

    quantity = int(call.data)
    if not 1 <= quantity <= 5:
        call.message.answer("Количество должно быть не меньше 1 и не больше 5")
        call.answer()
        return

    user_data = await state.get_data()
    item_data = user_data.get("item_data")

    cart = user_data["cart"]
    cart.append({
        "item": item_data["item"],
        "type": "product",
        "quantity": quantity,
        "price": item_data["price"],
        "callback_data": item_data["callback_data"]
    })

    await state.update_data(cart=cart)

    await call.message.answer(f"{item_data['item']} ({quantity} шт) добавлено в корзину. Хотите продолжить далее?", reply_markup= await get_main_menu_kb())
    await state.set_state(None)
    await call.answer()

