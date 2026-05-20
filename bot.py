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

TOKEN = "8791465958:AAGKi_Cebi5uG6B74ja6UPH4AH8H2ntxaXA"

CRYPTO_BOT_TOKEN = "584710:AAtD87zzLOvKArMkihQt1Q1bUVL2kLKzvru"

ADMIN_ID = 6313541727

API_URL = "https://pay.crypt.bot/api"

# =========================================================
# ЗАПУСК
# =========================================================

bot = Bot(token=TOKEN)

dp = Dispatcher(storage=MemoryStorage())

# =========================================================
# БАЗА
# =========================================================

DB_CATEGORIES = {}
DB_PRODUCTS = {}

cat_counter = 0

# =========================================================
# СОСТОЯНИЯ
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

    editing_category_name = State()

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
        [KeyboardButton(text="📂 Категории")],
        [KeyboardButton(text="+ Добавить товар")],
        [KeyboardButton(text="✏️ Редактировать товар")],
        [KeyboardButton(text="🗂 Редактировать категории")],
        [KeyboardButton(text="🚪 Выход")]
    ],
    resize_keyboard=True
)

# =========================================================
# CRYPTO BOT
# =========================================================

async def create_invoice(amount):

    url = f"{API_URL}/createInvoice"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN
    }

    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": "Покупка товара"
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(
            url,
            json=payload,
            headers=headers
        ) as response:

            data = await response.json()

            if data.get("ok"):
                return data["result"]

    return None


async def check_invoice(invoice_id):

    url = f"{API_URL}/getInvoices"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN
    }

    params = {
        "invoice_ids": invoice_id
    }

    async with aiohttp.ClientSession() as session:

        async with session.get(
            url,
            headers=headers,
            params=params
        ) as response:

            data = await response.json()

            if not data.get("ok"):
                return False

            items = data["result"]["items"]

            if not items:
                return False

            return items[0]["status"] == "paid"

# =========================================================
# START
# =========================================================

@dp.message(F.text == "/start")
async def start(message: Message):

    if message.from_user.id == ADMIN_ID:

        await message.answer(
            "⚡ Добро пожаловать в RazeShop",
            reply_markup=admin_menu
        )

    else:

        await message.answer(
            "⚡ Добро пожаловать в магазин",
            reply_markup=user_menu
        )

# =========================================================
# ПОДДЕРЖКА
# =========================================================

@dp.message(F.text == "💬 Поддержка")
async def support(message: Message):

    await message.answer(
        "💬 Техническая поддержка : @RazeShopsupport"
    )

# =========================================================
# КУПИТЬ
# =========================================================

@dp.message(F.text == "💵 Купить")
async def show_categories(message: Message):

    if not DB_CATEGORIES:
        await message.answer("❌ Категорий нет")
        return

    buttons = []

    for cat_id, cat_name in DB_CATEGORIES.items():

        buttons.append([
            InlineKeyboardButton(
                text=cat_name,
                callback_data=f"cat:{cat_id}"
            )
        ])

    await message.answer(
        "📦 Выберите товар",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

# =========================================================
# НАЛИЧИЕ
# =========================================================

@dp.message(F.text == "📊 Товар в наличии")
async def stock_products(message: Message):

    if not DB_PRODUCTS:
        await message.answer("❌ Товаров нет")
        return

    text = ""

    total = 0

    for cat_id, products in DB_PRODUCTS.items():

        category_name = DB_CATEGORIES.get(cat_id)

        text += f"➖➖➖📦 {category_name} 📦➖➖➖\n"

        for product in products:

            qty = len(product["data"])

            if qty <= 0:
                continue

            total += qty

            text += (
                f"➤ {product['name']} • "
                f"{product['price']}$ • "
                f"{qty} шт.\n"
            )

        text += "\n"

    text += f"📦 Всего товаров: {total}"

    await message.answer(text)

# =========================================================
# КАТЕГОРИЯ
# =========================================================

@dp.callback_query(F.data.startswith("cat:"))
async def show_products(call: CallbackQuery, state: FSMContext):

    cat_id = call.data.split(":")[1]

    products = DB_PRODUCTS.get(cat_id, [])

    if not products:
        await call.answer("❌ Товаров нет")
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

    await call.message.edit_text(
        "📦 Выберите товар",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await call.answer()

# =========================================================
# КАРТОЧКА
# =========================================================

@dp.callback_query(F.data.startswith("product:"))
async def product_card(call: CallbackQuery, state: FSMContext):

    _, cat_id, index = call.data.split(":")

    index = int(index)

    product = DB_PRODUCTS[cat_id][index]

    await state.update_data(
        cat_id=cat_id,
        product_index=index,
        price=product["price"]
    )

    qty = len(product["data"])

    text = (
        f"📦 Товар: {product['name']}\n\n"
        f"💰 Цена: {product['price']}$\n"
        f"📊 Наличие: {qty} шт.\n\n"
        f"📝 Описание:\n"
        f"{product['descr']}"
    )

    buttons = [
        [
            InlineKeyboardButton(
                text="💳 Купить",
                callback_data="buy_product"
            )
        ]
    ]

    await call.message.delete()

    await bot.send_photo(
        chat_id=call.message.chat.id,
        photo=product["photo"],
        caption=text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await call.answer()

# =========================================================
# ПОКУПКА
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
        [
            InlineKeyboardButton(
                text="💳 Оплатить",
                url=invoice["bot_invoice_url"]
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Проверить оплату",
                callback_data=f"check:{invoice['invoice_id']}"
            )
        ]
    ]

    await call.message.answer(
        f"💰 Счет создан\n\nСумма: {amount}$",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

# =========================================================
# ПРОВЕРКА ОПЛАТЫ
# =========================================================

@dp.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery, state: FSMContext):

    invoice_id = int(call.data.split(":")[1])

    paid = await check_invoice(invoice_id)

    if not paid:

        await call.answer(
            "❌ Оплата не найдена",
            show_alert=True
        )

        return

    data = await state.get_data()

    cat_id = data["cat_id"]

    product_index = data["product_index"]

    product = DB_PRODUCTS[cat_id][product_index]

    if not product["data"]:
        await call.message.answer("❌ Товар закончился")
        return

    item = product["data"].pop(0)

    await call.message.answer(
        f"✅ Оплата прошла\n\n📦 Ваш товар:\n\n`{item}`",
        parse_mode="Markdown"
    )

# =========================================================
# АДМИНКА
# =========================================================

@dp.message(F.text == "⚙️ Админка")
async def admin(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "⚙️ Админ панель",
        reply_markup=admin_panel
    )

# =========================================================
# ДОБАВЛЕНИЕ КАТЕГОРИИ
# =========================================================

@dp.message(F.text == "📂 Категории")
async def categories(message: Message):

    buttons = [
        [
            InlineKeyboardButton(
                text="➕ Добавить категорию",
                callback_data="add_category"
            )
        ]
    ]

    await message.answer(
        "📂 Управление категориями",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data == "add_category")
async def add_category(call: CallbackQuery, state: FSMContext):

    await call.message.answer("Введите название категории")

    await state.set_state(
        AdminStates.adding_category
    )

@dp.message(AdminStates.adding_category)
async def save_category(message: Message, state: FSMContext):

    global cat_counter

    cat_counter += 1

    cat_id = f"cat_{cat_counter}"

    DB_CATEGORIES[cat_id] = message.text

    DB_PRODUCTS[cat_id] = []

    await message.answer(
        f"✅ Категория {message.text} создана"
    )

    await state.clear()

# =========================================================
# ДОБАВИТЬ ТОВАР
# =========================================================

@dp.message(F.text == "+ Добавить товар")
async def add_product(message: Message):

    buttons = []

    for cat_id, name in DB_CATEGORIES.items():

        buttons.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"addproduct:{cat_id}"
            )
        ])

    await message.answer(
        "Выберите категорию",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data.startswith("addproduct:"))
async def add_product_category(call: CallbackQuery, state: FSMContext):

    cat_id = call.data.split(":")[1]

    await state.update_data(
        selected_category=cat_id
    )

    await call.message.answer("Введите название товара")

    await state.set_state(
        AdminStates.entering_prod_name
    )

@dp.message(AdminStates.entering_prod_name)
async def product_name(message: Message, state: FSMContext):

    await state.update_data(
        product_name=message.text
    )

    await message.answer("Введите цену товара")

    await state.set_state(
        AdminStates.entering_prod_price
    )

@dp.message(AdminStates.entering_prod_price)
async def product_price(message: Message, state: FSMContext):

    price = float(message.text)

    await state.update_data(
        product_price=price
    )

    await message.answer("Введите описание товара")

    await state.set_state(
        AdminStates.entering_prod_descr
    )

@dp.message(AdminStates.entering_prod_descr)
async def product_descr(message: Message, state: FSMContext):

    await state.update_data(
        product_descr=message.text
    )

    await message.answer("Отправьте фото товара")

    await state.set_state(
        AdminStates.entering_prod_photo
    )

@dp.message(AdminStates.entering_prod_photo, F.photo)
async def product_photo(message: Message, state: FSMContext):

    photo_id = message.photo[-1].file_id

    await state.update_data(
        product_photo=photo_id
    )

    await message.answer("Отправьте товары построчно")

    await state.set_state(
        AdminStates.entering_prod_data
    )

@dp.message(AdminStates.entering_prod_data)
async def product_finish(message: Message, state: FSMContext):

    data = await state.get_data()

    cat_id = data["selected_category"]

    items = [
        x.strip()
        for x in message.text.split("\n")
        if x.strip()
    ]

    product = {
        "name": data["product_name"],
        "price": data["product_price"],
        "descr": data["product_descr"],
        "photo": data["product_photo"],
        "data": items
    }

    DB_PRODUCTS[cat_id].append(product)

    await message.answer(
        f"✅ Товар {data['product_name']} добавлен"
    )

    await state.clear()

# =========================================================
# РЕДАКТИРОВАНИЕ ТОВАРА
# =========================================================

@dp.message(F.text == "✏️ Редактировать товар")
async def edit_products(message: Message):

    buttons = []

    for cat_id, products in DB_PRODUCTS.items():

        for index, product in enumerate(products):

            buttons.append([
                InlineKeyboardButton(
                    text=f"{product['name']} | {product['price']}$",
                    callback_data=f"edit:{cat_id}:{index}"
                )
            ])

    await message.answer(
        "✏️ Выберите товар",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data.startswith("edit:"))
async def edit_product_menu(call: CallbackQuery, state: FSMContext):

    _, cat_id, index = call.data.split(":")

    index = int(index)

    await state.update_data(
        edit_cat_id=cat_id,
        edit_index=index
    )

    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить название",
                callback_data="edit_name"
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 Изменить цену",
                callback_data="edit_price"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Изменить описание",
                callback_data="edit_descr"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 Удалить товар",
                callback_data="delete_product"
            )
        ]
    ]

    await call.message.edit_text(
        "⚙️ Управление товаром",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data == "delete_product")
async def delete_product(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    del DB_PRODUCTS[cat_id][index]

    await call.message.edit_text("🗑 Товар удален")

    await state.clear()

# =========================================================
# РЕДАКТИРОВАНИЕ КАТЕГОРИЙ
# =========================================================

@dp.message(F.text == "🗂 Редактировать категории")
async def edit_categories(message: Message):

    buttons = []

    for cat_id, cat_name in DB_CATEGORIES.items():

        buttons.append([
            InlineKeyboardButton(
                text=cat_name,
                callback_data=f"editcat:{cat_id}"
            )
        ])

    await message.answer(
        "🗂 Выберите категорию",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data.startswith("editcat:"))
async def category_edit_menu(call: CallbackQuery, state: FSMContext):

    cat_id = call.data.split(":")[1]

    await state.update_data(
        edit_category_id=cat_id
    )

    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Изменить название",
                callback_data="rename_category"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 Удалить категорию",
                callback_data="delete_category"
            )
        ]
    ]

    await call.message.edit_text(
        "⚙️ Управление категорией",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

@dp.callback_query(F.data == "rename_category")
async def rename_category(call: CallbackQuery, state: FSMContext):

    await call.message.answer(
        "Введите новое название категории"
    )

    await state.set_state(
        AdminStates.editing_category_name
    )

@dp.message(AdminStates.editing_category_name)
async def save_new_category_name(message: Message, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_category_id"]

    DB_CATEGORIES[cat_id] = message.text

    await message.answer(
        "✅ Название категории изменено"
    )

    await state.clear()

@dp.callback_query(F.data == "delete_category")
async def delete_category(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_category_id"]

    del DB_CATEGORIES[cat_id]
    del DB_PRODUCTS[cat_id]

    await call.message.edit_text(
        "🗑 Категория удалена"
    )

    await state.clear()

# =========================================================
# ИЗМЕНЕНИЕ НАЗВАНИЯ
# =========================================================

@dp.callback_query(F.data == "edit_name")
async def edit_name(call: CallbackQuery, state: FSMContext):

    await call.message.answer("Введите новое название")

    await state.set_state(
        AdminStates.editing_name
    )

@dp.message(AdminStates.editing_name)
async def save_new_name(message: Message, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["name"] = message.text

    await message.answer("✅ Название изменено")

    await state.clear()

# =========================================================
# ИЗМЕНЕНИЕ ЦЕНЫ
# =========================================================

@dp.callback_query(F.data == "edit_price")
async def edit_price(call: CallbackQuery, state: FSMContext):

    await call.message.answer("Введите новую цену")

    await state.set_state(
        AdminStates.editing_price
    )

@dp.message(AdminStates.editing_price)
async def save_new_price(message: Message, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["price"] = float(message.text)

    await message.answer("✅ Цена изменена")

    await state.clear()

# =========================================================
# ИЗМЕНЕНИЕ ОПИСАНИЯ
# =========================================================

@dp.callback_query(F.data == "edit_descr")
async def edit_descr(call: CallbackQuery, state: FSMContext):

    await call.message.answer("Введите новое описание")

    await state.set_state(
        AdminStates.editing_descr
    )

@dp.message(AdminStates.editing_descr)
async def save_new_descr(message: Message, state: FSMContext):

    data = await state.get_data()

    cat_id = data["edit_cat_id"]
    index = data["edit_index"]

    DB_PRODUCTS[cat_id][index]["descr"] = message.text

    await message.answer("✅ Описание изменено")

    await state.clear()

# =========================================================
# ВЫХОД
# =========================================================

@dp.message(F.text == "🚪 Выход")
async def exit_admin(message: Message):

    await message.answer(
        "Вы вышли из админки",
        reply_markup=admin_menu
    )

# =========================================================
# ЗАПУСК
# =========================================================

async def main():

    print("RazeShop запущен!")

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())