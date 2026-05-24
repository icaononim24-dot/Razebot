import asyncio
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# =========================================================
# НАСТРОЙКИ
# =========================================================

TOKEN = "8890721927:AAE-lJnSNFCpA1VX1jiwfGNRDHqQTafKUaY"
CRYPTO_BOT_TOKEN = "584710:AAtD87zzLOvKArMkihQt1Q1bUVL2kLKzvru"
ADMIN_ID = 6313541727
API_URL = "https://pay.crypt.bot/api"

# =========================================================
# ЗАПУСК
# =========================================================

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =========================================================
# БАЗА ДАННЫХ (В ОЗУ)
# =========================================================

DB_CATEGORIES = {}
DB_PRODUCTS = {}
cat_counter = 0


# =========================================================
# СОСТОЯНИЯ (FSM)
# =========================================================

class AdminStates(StatesGroup):
    adding_category = State()

    entering_prod_name = State()
    entering_prod_price = State()
    entering_prod_descr = State()
    entering_prod_photo = State()
    entering_prod_data = State()

    editing_name = State()
    editing_price = State()
    editing_descr = State()
    restocking_prod = State()


# =========================================================
# КНОПКИ
# =========================================================

user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Купить")],
        [KeyboardButton(text="📊 Товар в наличии")],
        [KeyboardButton(text="💬 Поддержка")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💵 Купить")],
        [KeyboardButton(text="📊 Товар в наличии")],
        [KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="⚙️ Админка")]
    ],
    resize_keyboard=True
)

admin_panel = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛠 Редактор")],
        [KeyboardButton(text="🚪 Выход")]
    ],
    resize_keyboard=True
)

editor_panel = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Категории")],
        [KeyboardButton(text="+ Добавить товар")],
        [KeyboardButton(text="✏️ Редактировать товар")],
        [KeyboardButton(text="⬅️ Назад в админку")]
    ],
    resize_keyboard=True
)


# =========================================================
# CRYPTO BOT API
# =========================================================

async def create_invoice(amount):
    url = f"{API_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": "Покупка товара"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if data.get("ok"):
                    return data["result"]
    except Exception as e:
        print("Ошибка create_invoice:", e)
    return None


async def check_invoice(invoice_id):
    url = f"{API_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
                if not data.get("ok"):
                    return False
                items = data["result"]["items"]
                if not items:
                    return False
                return items[0]["status"] == "paid"
    except Exception as e:
        print("Ошибка check_invoice:", e)
    return False


# =========================================================
# КОМАНДА /START
# =========================================================

@dp.message(F.text == "/start")
async def start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("⚡ Добро пожаловать в RazeShop", reply_markup=admin_menu)
    else:
        await message.answer("⚡ Добро пожаловать в магазин", reply_markup=user_menu)


# =========================================================
# ПОДДЕРЖКА
# =========================================================

@dp.message(F.text == "💬 Поддержка")
async def support(message: Message):
    await message.answer("💬 Техническая поддержка : @RazeShopsupport")


# =========================================================
# КУПИТЬ (МЕНЮ ДЛЯ ЮЗЕРА)
# =========================================================

@dp.message(F.text == "💵 Купить")
async def show_categories(message: Message):
    if not DB_CATEGORIES:
        await message.answer("❌ Категорий нет")
        return

    buttons = []
    for cat_id, cat_name in DB_CATEGORIES.items():
        buttons.append([InlineKeyboardButton(text=cat_name, callback_data=f"cat:{cat_id}")])

    await message.answer("📦 Выберите товар", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


# =========================================================
# ТОВАР В НАЛИЧИИ
# =========================================================

@dp.message(F.text == "📊 Товар в наличии")
async def stock_products(message: Message):
    if not DB_PRODUCTS:
        await message.answer("❌ Товаров нет")
        return

    text = ""
    total = 0
    for cat_id, products in DB_PRODUCTS.items():
        category_name = DB_CATEGORIES.get(cat_id, "Категория")
        text += f"➖➖➖📦 {category_name} 📦➖➖➖\n"
        for product in products:
            qty = len(product["data"])
            if qty <= 0:
                continue
            total += qty
            text += f"➤ {product['name']} • {product['price']}$ • {qty} шт.\n"
        text += "\n"

    text += f"📦 Всего товаров: {total}"
    await message.answer(text)


# =========================================================
# ВЫБОР КАТЕГОРИИ И ВЫВОД ТОВАРОВ
# =========================================================

@dp.callback_query(F.data.startswith("cat:"))
async def show_products(call: CallbackQuery, state: FSMContext):
    cat_id = call.data.split(":")[1]
    products = DB_PRODUCTS.get(cat_id, [])

    if not products:
        await call.answer("❌ Товаров нет")
        return

    if len(products) == 1:
        product = products[0]
        await state.update_data(cat_id=cat_id, product_index=0, price=product["price"])
        qty = len(product["data"])

        text = (
            f"📦 Товар: {product['name']}\n\n"
            f"💰 Цена: {product['price']}$\n"
            f"📊 Наличие: {qty} шт.\n\n"
            f"📝 Описание:\n{product['descr']}"
        )

        buttons = [[InlineKeyboardButton(text="💳 Купить", callback_data="buy_product")]]
        await call.message.delete()

        # Если фото было пропущено (равно None), отправляем только текст
        if product["photo"] is None:
            await bot.send_message(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        else:
            await bot.send_photo(
                chat_id=call.message.chat.id,
                photo=product["photo"],
                caption=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        await call.answer()
        return

    buttons = []
    for index, product in enumerate(products):
        qty = len(product["data"])
        buttons.append([
            InlineKeyboardButton(
                text=f"{product['name']} • {product['price']}$ • {qty} шт.",
                callback_data=f"product:{cat_id}:{index}"
            )
        ])

    await call.message.edit_text("📦 Выберите товар", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


# =========================================================
# КАРТОЧКА КОНКРЕТНОГО ТОВАРА
# =========================================================

@dp.callback_query(F.data.startswith("product:"))
async def product_card(call: CallbackQuery, state: FSMContext):
    _, cat_id, index = call.data.split(":")
    index = int(index)
    product = DB_PRODUCTS[cat_id][index]

    await state.update_data(cat_id=cat_id, product_index=index, price=product["price"])
    qty = len(product["data"])

    text = (
        f"📦 Товар: {product['name']}\n\n"
        f"💰 Цена: {product['price']}$\n"
        f"📊 Наличие: {qty} шт.\n\n"
        f"📝 Описание:\n{product['descr']}"
    )

    buttons = [[InlineKeyboardButton(text="💳 Купить", callback_data="buy_product")]]
    await call.message.delete()

    # Корректное отображение карточки товара без фото
    if product["photo"] is None:
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await bot.send_photo(
            chat_id=call.message.chat.id,
            photo=product["photo"],
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    await call.answer()


# =========================================================
# ПРОЦЕСС ПОКУПКИ (СОЗДАНИЕ СЧЕТА)
# =========================================================

@dp.callback_query(F.data == "buy_product")
async def buy_product(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data["price"]
    invoice = await create_invoice(amount)

    if not invoice:
        await call.message.answer("❌ Ошибка создания счета")
        return

    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", url=invoice["bot_invoice_url"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check:{invoice['invoice_id']}")]
    ]

    await call.message.answer(
        f"💰 Счет создан\n\nСумма: {amount}$",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()


# =========================================================
# ПРОВЕРКА ОПЛАТЫ И ВЫДАЧА ТОВАРА
# =========================================================

@dp.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery, state: FSMContext):
    invoice_id = int(call.data.split(":")[1])
    paid = await check_invoice(invoice_id)

    if not paid:
        await call.answer("❌ Оплата не найдена", show_alert=True)
        return

    data = await state.get_data()
    cat_id = data["cat_id"]
    product_index = data["product_index"]
    product = DB_PRODUCTS[cat_id][product_index]

    if not product["data"]:
        await call.message.answer("❌ Товар закончился")
        return

    item = product["data"].pop(0)
    await call.message.answer(f"✅ Оплата прошла\n\n📦 Ваш товар:\n\n`{item}`", parse_mode="Markdown")
    await call.answer()


# =========================================================
# АДМИН ПАНЕЛЬ
# =========================================================

@dp.message(F.text == "⚙️ Админка")
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("⚙️ Админ панель", reply_markup=admin_panel)


@dp.message(F.text == "🛠 Редактор")
async def open_editor(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🛠 Меню управления магазином", reply_markup=editor_panel)


@dp.message(F.text == "⬅️ Назад в админку")
async def back_to_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("⚙️ Возврат в главное админ-меню", reply_markup=admin_panel)


# =========================================================
# УПРАВЛЕНИЕ КАТЕГОРИЯМИ
# =========================================================

@dp.message(F.text == "📂 Категории")
async def categories(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    buttons = [[InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")]]
    await message.answer("📂 Управление категориями", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data == "add_category")
async def add_category(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите название категории")
    await state.set_state(AdminStates.adding_category)
    await call.answer()


@dp.message(AdminStates.adding_category)
async def save_category(message: Message, state: FSMContext):
    global cat_counter
    cat_counter += 1
    cat_id = f"cat_{cat_counter}"

    DB_CATEGORIES[cat_id] = message.text
    DB_PRODUCTS[cat_id] = []

    await message.answer(f"✅ Категория {message.text} создана")
    await state.clear()


# =========================================================
# ДОБАВЛЕНИЕ НОВОГО ТОВАРА С НУЛЯ
# =========================================================

@dp.message(F.text == "+ Добавить товар")
async def add_product(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not DB_CATEGORIES:
        await message.answer("❌ Сначала создайте категорию")
        return

    buttons = []
    for cat_id, name in DB_CATEGORIES.items():
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"addproduct:{cat_id}")])

    await message.answer("Выберите категорию", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data.startswith("addproduct:"))
async def add_product_category(call: CallbackQuery, state: FSMContext):
    cat_id = call.data.split(":")[1]
    await state.update_data(selected_category=cat_id)
    await call.message.answer("Введите название товара")
    await state.set_state(AdminStates.entering_prod_name)
    await call.answer()


@dp.message(AdminStates.entering_prod_name)
async def product_name(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("Введите цену товара")
    await state.set_state(AdminStates.entering_prod_price)


@dp.message(AdminStates.entering_prod_price)
async def product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except:
        await message.answer("Введите число")
        return

    await state.update_data(product_price=price)
    await message.answer("Введите описание товара")
    await state.set_state(AdminStates.entering_prod_descr)


@dp.message(AdminStates.entering_prod_descr)
async def product_descr(message: Message, state: FSMContext):
    await state.update_data(product_descr=message.text)
    # Изменено: Добавили подсказку о возможности пропуска загрузки фото
    await message.answer("Отправьте фото товара или введите /skip, чтобы продолжить создание без фото")
    await state.set_state(AdminStates.entering_prod_photo)


# Изменено: Хэндлер принимает фото ИЛИ текст, обрабатывая команду /skip
@dp.message(AdminStates.entering_prod_photo, F.photo | F.text)
async def product_photo(message: Message, state: FSMContext):
    if message.text == "/skip":
        photo_id = None
        await message.answer("Шаг с фотографией пропущен.")
    elif message.photo:
        photo_id = message.photo[-1].file_id
    else:
        await message.answer("Пожалуйста, отправьте фото товара или напишите /skip")
        return

    await state.update_data(product_photo=photo_id)
    await message.answer("Отправьте товары построчно")
    await state.set_state(AdminStates.entering_prod_data)


@dp.message(AdminStates.entering_prod_data)
async def product_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data["selected_category"]

    items = [x.strip() for x in message.text.split("\n") if x.strip()]

    product = {
        "name": data["product_name"],
        "price": data["product_price"],
        "descr": data["product_descr"],
        "photo": data["product_photo"],
        "data": items
    }

    DB_PRODUCTS[cat_id].append(product)
    await message.answer(f"✅ Товар {data['product_name']} добавлен")
    await state.clear()


# =========================================================
# РЕДАКТИРОВАНИЕ И ПОПОЛНЕНИЕ ТОВАРОВ
# =========================================================

@dp.message(F.text == "✏️ Редактировать товар")
async def edit_products(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    buttons = []
    for cat_id, products in DB_PRODUCTS.items():
        for index, product in enumerate(products):
            buttons.append([
                InlineKeyboardButton(
                    text=f"{product['name']} | {product['price']}$",
                    callback_data=f"edit:{cat_id}:{index}"
                )
            ])

    if not buttons:
        await message.answer("❌ Товаров нет")
        return

    await message.answer("✏️ Выберите товар", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.callback_query(F.data.startswith("edit:"))
async def edit_product_menu(call: CallbackQuery, state: FSMContext):
    _, cat_id, index = call.data.split(":")
    index = int(index)

    await state.update_data(edit_cat_id=cat_id, edit_index=index)

    buttons = [
        [InlineKeyboardButton(text="📦 Пополнить товар", callback_data="edit_restock")],
        [InlineKeyboardButton(text="✏️ Название", callback_data="edit_name")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="edit_price")],
        [InlineKeyboardButton(text="📝 Описание", callback_data="edit_descr")]
    ]

    await call.message.edit_text("⚙️ Что хотите изменить?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()


@dp.callback_query(F.data == "edit_restock")
async def edit_restock(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Отправьте новые товары построчно.\nКаждая новая строка будет добавлена к текущему остатку."
    )
    await state.set_state(AdminStates.restocking_prod)
    await call.answer()


@dp.message(AdminStates.restocking_prod)
async def save_restocked_data(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    new_items = [x.strip() for x in message.text.split("\n") if x.strip()]

    if not new_items:
        await message.answer("❌ Вы прислали пустой текст. Попробуйте еще раз.")
        return

    DB_PRODUCTS[cat_id][index]["data"].extend(new_items)

    prod_name = DB_PRODUCTS[cat_id][index]['name']
    current_qty = len(DB_PRODUCTS[cat_id][index]['data'])

    await message.answer(
        f"✅ Товар успешно пополнен!\n"
        f"Добавлено позиций: {len(new_items)} шт.\n"
        f"Всего в наличии у {prod_name}: {current_qty} шт."
    )
    await state.clear()


# =========================================================
# ИЗМЕНЕНИЕ ХАРАКТЕРИСТИК (НАЗВАНИЕ, ЦЕНА, ОПИСАНИЕ)
# =========================================================

@dp.callback_query(F.data == "edit_name")
async def edit_name(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое название")
    await state.set_state(AdminStates.editing_name)
    await call.answer()


@dp.message(AdminStates.editing_name)
async def save_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["name"] = message.text
    await message.answer("✅ Название изменено")
    await state.clear()


@dp.callback_query(F.data == "edit_price")
async def edit_price(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новую цену")
    await state.set_state(AdminStates.editing_price)
    await call.answer()


@dp.message(AdminStates.editing_price)
async def save_new_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except:
        await message.answer("Введите число")
        return

    data = await state.get_data()
    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["price"] = price
    await message.answer("✅ Цена изменена")
    await state.clear()


@dp.callback_query(F.data == "edit_descr")
async def edit_descr(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое описание")
    await state.set_state(AdminStates.editing_descr)
    await call.answer()


@dp.message(AdminStates.editing_descr)
async def save_new_descr(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["descr"] = message.text
    await message.answer("✅ Описание изменено")
    await state.clear()


# =========================================================
# ВЫХОД ИЗ АДМИНКИ БОТА
# =========================================================

@dp.message(F.text == "🚪 Выход")
async def exit_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Вы вышли из админки", reply_markup=admin_menu)


# =========================================================
# ЗАПУСК БОТА
# =========================================================

async def main():
    print("RazeShop запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())