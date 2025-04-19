from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date

from data_manager import DataManager

common_router = Router()
data_manager = DataManager()


class CartStates(StatesGroup):
    viewing_cart = State()


async def get_cart_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Оформить заказ", callback_data="confirm_order")
    builder.button(text="Очистить корзину", callback_data="clear_cart")
    builder.adjust(1)
    return builder.as_markup()


async def get_main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="Товары")
    builder.button(text="Курсы")
    builder.button(text="Корзина")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


@common_router.message(F.text == "Корзина")
@common_router.message(Command(commands="cart"))
async def view_cart(message: Message, state: FSMContext):
    '''Показ корзины'''
    user_data = await state.get_data()
    cart = user_data.get("cart", [])

    kb = await get_cart_kb()

    if not cart:
        await message.answer("Ваша корзина пуста")
        return

    total_price = sum(item["quantity"] * item["price"] for item in cart)
    response = "Ваша корзина: \n"
    for item in cart:
        item_type = "Товар" if item["type"] == "product" else "Курс"
        response += f" - {item_type}: {item['item']} ({item['quantity']} шт) - {item['quantity'] * item['price']} руб \n"

    response += f"Итого - {total_price} руб"

    await message.answer(response, reply_markup=kb)
    await state.set_state(CartStates.viewing_cart)


@common_router.callback_query(CartStates.viewing_cart, F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    '''Подтверждение заказа'''
    user_data = await state.get_data()
    cart = user_data.get("cart", [])

    if not cart:
        await call.message.answer("Ваша корзина пуста")
        await call.answer()
        return

    user_id = call.from_user.id
    for item in cart:
        order_data = {
            "item": item["item"],
            "type": item["type"],
            "price": item["price"] * item["quantity"],
            "paid": False,
            "date": date.today().isoformat()
        }
        await data_manager.add_order(user_id, order_data)

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("Ваш заказ сформирован")
    await state.clear()
    await call.answer()


@common_router.callback_query(CartStates.viewing_cart, F.data == "clear_cart")
async def clear_cart(call: CallbackQuery, state: FSMContext):
    '''Очищение корзины'''
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer("Ваша корзина очищена")
    await call.answer()


@common_router.message(Command(commands="start"))
async def start_command(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Я бот кондитерской СофиКо\n"
        "Для заказа товаров введите /order\n"
        "Для просмотра списка курсов введите /courses\n"
        "Для просмотра корзины введите /cart",
        reply_markup=await get_main_menu_kb()
    )


@common_router.message(Command(commands="about"))
async def about_command(message: Message):
    """Обработчик команды /about."""
    await message.answer("Мы — кондитерская СофиКо! Печем торты и учим других")