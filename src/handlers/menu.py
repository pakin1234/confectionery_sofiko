from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import os

from data_manager import DataManager
from handlers.common import get_main_menu_kb

data_manager = DataManager()
menu_router = Router()


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MAX_QUANTITY = 5
ERROR_IMAGE_NOT_FOUND = "\n\n(Изображение товара не найдено)"
ERROR_IMAGE_UPLOAD_FAILED = "\n\n(Не удалось загрузить изображение товара)"
ERROR_QUANTITY_ADJUST_FAILED = "Произошла ошибка при изменении количества. Попробуйте еще раз."
ERROR_ITEM_NOT_FOUND = "Товар не найден"
ERROR_ITEM_DATA_MISSING = "Ошибка: данные товара не найдены. Попробуйте выбрать товар заново."

class OrderStates(StatesGroup):
    choosing_item = State()
    adjusting_quantity = State() 


def _format_item_description(item_data, quantity: int) -> str:
    """Форматирует описание товара с указанием количества."""
    return (
        f"<b>{item_data['item']}</b>\n"
        f"<b>Стоимость:</b> {item_data['price']} руб.\n\n"
        f"Вы выбрали '{item_data['item']}'. Количество: {quantity}\n"
        f"Хотите изменить количество или подтвердить выбор? (максимум {MAX_QUANTITY} шт.)"
    )


async def get_category_kb() -> InlineKeyboardMarkup:
    """Генерирует inline-клавиатуру с категориями."""
    products_data = await data_manager.load_products_base()
    builder = InlineKeyboardBuilder()
    for category in products_data:
        builder.button(text=category["name"], callback_data=category["category"])
    builder.adjust(1)
    return builder.as_markup()

async def get_item_kb(category_callback: str) -> InlineKeyboardMarkup:
    """Генерирует inline-клавиатуру с товарами."""
    products_data = await data_manager.load_products_base()
    builder = InlineKeyboardBuilder()
    for category in products_data:
        if category["category"] == category_callback:
            for item in category["items"]:
                builder.button(text=item["item"], callback_data=item["callback_data"])
            break
    builder.adjust(2)
    return builder.as_markup()

async def get_quantity_adjust_kb() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру для изменения количества товаров."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Уменьшить (-1)", callback_data="decrease")
    builder.button(text="Увеличить (+1)", callback_data="increase")
    builder.button(text="Подтвердить", callback_data="confirm")
    builder.adjust(2)
    return builder.as_markup()


@menu_router.message(F.text == "Товары")
@menu_router.message(Command(commands="order"))
async def start_order(message: Message, state: FSMContext):
    """Обработчик команды /order или текста 'Товары'."""
    user_data = await state.get_data()
    if "cart" not in user_data:
        await state.update_data(cart=[])

    kb = await get_category_kb()
    if not kb.inline_keyboard:
        await message.answer("Извините, товары временно недоступны.", reply_markup=await get_main_menu_kb())
        return
    
    await message.answer("Выберите категорию:", reply_markup=kb)
    await state.set_state(None)

@menu_router.callback_query(F.data.in_({"cupcake", "cake", "bouquet"}))
async def order_item(call: CallbackQuery, state: FSMContext):
    """Обработчик выбора категории."""
    category = call.data
    await state.update_data(category=category)
    kb = await get_item_kb(category)
    if not kb.inline_keyboard:
        await call.message.answer("В этой категории нет товаров.", reply_markup=await get_main_menu_kb())
        await call.answer()
        return
    await call.message.answer("Выберите, что вы хотите заказать:", reply_markup=kb)
    await state.set_state(OrderStates.choosing_item)
    await call.answer()

@menu_router.callback_query(OrderStates.choosing_item)
async def select_item(call: CallbackQuery, state: FSMContext):
    """Обработчик выбора товара."""
    item_callback = call.data
    products_data = await data_manager.load_products_base()
    item_data = None
    user_data = await state.get_data()
    category_data = user_data.get("category")

    for categ in products_data:
        if categ["category"] == category_data:
            for item in categ["items"]:
                if item["callback_data"] == item_callback:
                    item_data = item
                    break
            break

    if not item_data:
        await call.message.answer(ERROR_ITEM_NOT_FOUND, reply_markup=await get_main_menu_kb())
        await call.answer()
        return

    description = _format_item_description(item_data, quantity=1)
    kb = await get_quantity_adjust_kb()

    is_photo = False
    if item_data.get("image_url"):
        image_path = os.path.join(BASE_DIR, item_data["image_url"])
        if os.path.exists(image_path):
            try:
                with open(image_path, "rb") as photo_file:
                    photo = BufferedInputFile(photo_file.read(), filename=os.path.basename(image_path))
                await call.message.answer_photo(
                    photo=photo,
                    caption=description,
                    parse_mode="HTML",
                    reply_markup=kb
                )
                is_photo = True
            except TelegramBadRequest:
                await call.message.answer(
                    text=description + ERROR_IMAGE_UPLOAD_FAILED,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except Exception:
                await call.message.answer(
                    text=description + ERROR_IMAGE_UPLOAD_FAILED,
                    parse_mode="HTML",
                    reply_markup=kb
                )
        else:
            await call.message.answer(
                text=description + ERROR_IMAGE_NOT_FOUND,
                parse_mode="HTML",
                reply_markup=kb
            )
    else:
        await call.message.answer(
            text=description,
            parse_mode="HTML",
            reply_markup=kb
        )

    await state.update_data(item_data=item_data, quantity=1, is_photo=is_photo)
    await state.set_state(OrderStates.adjusting_quantity)
    await call.answer()

@menu_router.callback_query(OrderStates.adjusting_quantity, F.data.in_({"decrease", "increase", "confirm"}))
async def adjust_quantity(call: CallbackQuery, state: FSMContext):
    """Обработчик изменения количества товаров или подтверждения."""
    # Проверяем наличие данных товара
    user_data = await state.get_data()
    quantity = user_data.get("quantity", 1)
    item_data = user_data.get("item_data")
    is_photo = user_data.get("is_photo", False)

    if not item_data:
        await call.message.answer(ERROR_ITEM_DATA_MISSING, reply_markup=await get_main_menu_kb())
        await state.set_state(None)
        await call.answer()
        return

    # Обработка изменения количества
    kb = await get_quantity_adjust_kb()
    if call.data in {"decrease", "increase"}:
        if call.data == "decrease" and quantity > 1:
            quantity -= 1
        elif call.data == "increase" and quantity < MAX_QUANTITY:
            quantity += 1
        else:
            await call.answer()
            return

        await state.update_data(quantity=quantity)
        description = _format_item_description(item_data, quantity)

        try:
            if is_photo:
                await call.message.edit_caption(
                    caption=description,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            else:
                await call.message.edit_text(
                    text=description,
                    parse_mode="HTML",
                    reply_markup=kb
                )
        except Exception:
            await call.message.answer(
                text=ERROR_QUANTITY_ADJUST_FAILED,
                reply_markup=kb
            )
        await call.answer()
        return

    # Подтверждение выбора
    if call.data == "confirm":
        cart = user_data["cart"]
        cart.append({
            "item": item_data["item"],
            "type": "product",
            "quantity": quantity,
            "price": item_data["price"],
            "callback_data": item_data["callback_data"]
        })

        await state.update_data(cart=cart)
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(
            f"Товар '{item_data['item']}' ({quantity} шт.) добавлен в корзину. Хотите продолжить?",
            reply_markup=await get_main_menu_kb()
        )
        await state.set_state(None)
        await call.answer()

# from aiogram import Router, F
# from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardRemove
# from aiogram.filters import Command
# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.fsm.context import FSMContext

# from data_manager import DataManager
# from handlers.common import get_main_menu_kb

# data_manager = DataManager()
# menu_router = Router()

# class OrderStates(StatesGroup):
#     choosing_item = State()
#     entering_quantity = State()


# async def get_category_kb() -> InlineKeyboardMarkup:
#     products_data = await data_manager.load_products_base()
#     builder = InlineKeyboardBuilder()
#     for category in products_data:
#         builder.button(text=category["name"], callback_data=category["category"])
#     builder.adjust(1)
#     return builder.as_markup()

# async def get_item_kb(category_callback) -> InlineKeyboardMarkup:
#     products_data = await data_manager.load_products_base()
#     builder = InlineKeyboardBuilder()
#     for category in products_data:
#         if category["category"] == category_callback:
#             for item in category["items"]:
#                 builder.button(text=item["item"], callback_data=item["callback_data"])
#             break
#     builder.adjust(2)
#     return builder.as_markup()

# async def get_quantity_kb() -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     builder.button(text="1", callback_data="1")
#     builder.button(text="2", callback_data="2")
#     builder.button(text="3", callback_data="3")
#     builder.button(text="4", callback_data="4")
#     builder.button(text="5", callback_data="5")
#     builder.adjust(1)
#     return builder.as_markup()


# @menu_router.message(F.text == "Товары")
# @menu_router.message(Command(commands="order"))
# async def start_order(message: Message, state: FSMContext):
#     user_data = await state.get_data()
#     if "cart" not in user_data:
#         await state.update_data(cart=[])

#     kb = await get_category_kb()
# # Убираем reply-клавиатуру и показываем inline-клавиатуру
#     await message.answer("Выберите категорию:", reply_markup=kb)
#     await message.answer("Категории:", reply_markup=ReplyKeyboardRemove())
#     await state.set_state(None)

# @menu_router.callback_query(F.data.in_({"cupcake", "cake", "bouquet"}))
# async def order_item(call: CallbackQuery,state: FSMContext):
#     category = call.data
#     await state.update_data(category=category)
#     kb = await get_item_kb(category)
#     await call.message.answer("Выберите, что вы хотите заказать", reply_markup=kb)
#     await state.set_state(OrderStates.choosing_item)
#     await call.answer()

# @menu_router.callback_query(OrderStates.choosing_item)
# async def select_item(call: CallbackQuery, state: FSMContext):
#     item_callback = call.data
#     products_data = await data_manager.load_products_base()
#     item_data = None
#     user_data = await state.get_data()
#     category_data = user_data.get("category")

#     kb = await get_quantity_kb()

#     for categ in products_data:
#         if categ["category"] == category_data:
#             for item in categ["items"]:
#                 if item["callback_data"] == item_callback:
#                     item_data = item
#                     break
#             break

#     if not item_data:
#         call.message.answer("Товар не найден")
#         call.answer()
#         return
    
#     await state.update_data(item_data=item_data)
#     await call.message.answer(f"Вы выбрали {item_data['item']}. Сколько Вы хотите заказать? (Введите число)", reply_markup=kb)
#     await state.set_state(OrderStates.entering_quantity)
#     await call.answer()

# @menu_router.callback_query(OrderStates.entering_quantity, F.data.in_({"1", "2", "3", "4", "5"}))
# async def enter_quantity(call: CallbackQuery, state: FSMContext):
#     kb = await get_category_kb()

#     quantity = int(call.data)
#     if not 1 <= quantity <= 5:
#         call.message.answer("Количество должно быть не меньше 1 и не больше 5")
#         call.answer()
#         return

#     user_data = await state.get_data()
#     item_data = user_data.get("item_data")

#     cart = user_data["cart"]
#     cart.append({
#         "item": item_data["item"],
#         "type": "product",
#         "quantity": quantity,
#         "price": item_data["price"],
#         "callback_data": item_data["callback_data"]
#     })

#     await state.update_data(cart=cart)

#     await call.message.answer(f"{item_data['item']} ({quantity} шт) добавлено в корзину. Хотите продолжить далее?", reply_markup= await get_main_menu_kb())
#     await state.set_state(None)
#     await call.answer()
