from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
import os

from data_manager import DataManager
from handlers.common import get_main_menu_kb

MAX_QUANTITY = 5
ERROR_IMAGE_NOT_FOUND = "\n\n(Изображение курса не найдено)"
ERROR_IMAGE_UPLOAD_FAILED = "\n\n(Не удалось загрузить изображение курса)"
ERROR_QUANTITY_ADJUST_FAILED = "Произошла ошибка при изменении количества. Попробуйте еще раз."
ERROR_COURSE_NOT_FOUND = "Курс не найден"
ERROR_COURSE_DATA_MISSING = "Ошибка: данные курса не найдены. Попробуйте выбрать курс заново."

# Определяем базовый путь до корня проекта
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

data_manager = DataManager()
courses_router = Router()

# Определение состояний FSM
class CourseOrderStates(StatesGroup):
    choosing_course = State()
    adjusting_quantity = State()

# Вспомогательные функции
def _format_course_description(course_data, quantity: int) -> str:
    """Форматирует описание курса с указанием количества мест."""
    return (
        f"<b>{course_data.item}</b>\n"
        f"{course_data.description}\n"
        f"<b>Стоимость:</b> {course_data.price} руб.\n\n"
        f"Вы выбрали курс '{course_data.item}'. Количество мест: {quantity}\n"
        f"Хотите изменить количество мест или подтвердить выбор? (максимальное количество мест - {MAX_QUANTITY})"
    )

async def get_courses_kb() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру со списком курсов."""
    courses_data = await data_manager.load_courses_base()
    builder = InlineKeyboardBuilder()
    if not courses_data:
        builder.button(text="Курсы отсутствуют", callback_data="no_courses")
    else:
        for course in courses_data:
            builder.button(text=course.item, callback_data=f"course_{course.item}")
    builder.adjust(1)
    return builder.as_markup()

async def get_quantity_adjust_kb() -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру для изменения количества мест."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Уменьшить (-1)", callback_data="decrease")
    builder.button(text="Увеличить (+1)", callback_data="increase")
    builder.button(text="Подтвердить", callback_data="confirm")
    builder.adjust(2)
    return builder.as_markup()

# Обработчики
@courses_router.message(F.text == "Курсы")
@courses_router.message(Command(commands=["courses"]))  # Разделили фильтры на два декоратора
async def start_course_order(message: Message, state: FSMContext) -> None:
    """Обработчик для начала заказа курсов через текст 'Курсы' или команду /courses."""
    user_data = await state.get_data()
    if "cart" not in user_data:
        await state.update_data(cart=[])

    kb = await get_courses_kb()
    await message.answer("Выберите курс:", reply_markup=kb)
    await state.set_state(None)

@courses_router.callback_query(F.data.startswith("course_"))
async def select_course(call: CallbackQuery, state: FSMContext) -> None:
    """Обработчик выбора курса."""
    # Сбрасываем состояние перед новым выбором
    await state.set_state(None)

    # Извлекаем имя курса из callback_data
    course_name = call.data[len("course_"):]
    courses_data = await data_manager.load_courses_base()
    course_data = next((course for course in courses_data if course.item == course_name), None)

    if not course_data:
        await call.message.answer(ERROR_COURSE_NOT_FOUND)
        await call.answer()
        return

    # Формируем описание курса
    description = _format_course_description(course_data, quantity=1)
    kb = await get_quantity_adjust_kb()

    # Проверяем и отправляем изображение, если оно есть
    is_photo = False
    if course_data.image_url:
        image_path = os.path.join(BASE_DIR, course_data.image_url)
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

    # Сохраняем данные в состоянии
    await state.update_data(course_data=course_data, quantity=1, is_photo=is_photo)
    await state.set_state(CourseOrderStates.adjusting_quantity)
    await call.answer()

@courses_router.callback_query(CourseOrderStates.adjusting_quantity, F.data.in_({"decrease", "increase", "confirm"}))
async def adjust_quantity(call: CallbackQuery, state: FSMContext) -> None:
    """Обработчик изменения количества мест или подтверждения."""
    # Проверяем наличие данных курса
    user_data = await state.get_data()
    quantity = user_data.get("quantity", 1)
    course_data = user_data.get("course_data")
    is_photo = user_data.get("is_photo", False)

    if not course_data:
        await call.message.answer(ERROR_COURSE_DATA_MISSING)
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
        description = _format_course_description(course_data, quantity)

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
            "item": course_data.item,
            "type": "course",
            "quantity": quantity,
            "price": course_data.price,
            "callback_data": f"course_{course_data.item}",
            "description": course_data.description
        })

        await state.update_data(cart=cart)
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(
            f"Курс '{course_data.item}' ({quantity} шт.) добавлен в корзину. Хотите продолжить?",
            reply_markup=await get_main_menu_kb()
        )
        await state.set_state(None)
        await call.answer()