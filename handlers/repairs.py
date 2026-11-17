from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import (
    add_repair as db_add_repair,
    get_all_repairs,
    get_repair_by_id,
    update_repair,
    delete_repair as db_delete_repair
)


router = Router()

VALID_STATUSES = {
    "Pending",
    "In Progress",
    "Completed"
}

MAX_NAME_LENGTH = 100
MAX_DEVICE_LENGTH = 100
MAX_PROBLEM_LENGTH = 1000
MAX_PRICE_LENGTH = 18


class RepairForm(StatesGroup):
    customer_name = State()
    device = State()
    problem = State()
    price = State()


class EditRepairForm(StatesGroup):
    new_value = State()


def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
    )


def get_edit_keyboard(repair_id, user_id):
    fields = [
        ("Customer Name", "customer_name"),
        ("Device", "device"),
        ("Problem", "problem"),
        ("Price", "price")
    ]

    keyboard = []

    for label, field in fields:
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {label}",
                callback_data=f"edit_field:{field}:{repair_id}:{user_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Back to Menu",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_status_keyboard(repair_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Pending",
                    callback_data=f"status_set:{repair_id}:Pending:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔧 In Progress",
                    callback_data=f"status_set:{repair_id}:In Progress:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Completed",
                    callback_data=f"status_set:{repair_id}:Completed:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
    )


def get_delete_keyboard(repair_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yes, Delete",
                    callback_data=f"delete_confirm:{repair_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"delete_cancel:{user_id}"
                )
            ]
        ]
    )


def format_repair(repair):
    return (
        f"🔧 REPAIR #{repair[0]}\n\n"
        f"👤 Customer: {repair[1]}\n"
        f"📱 Device: {repair[2]}\n"
        f"🛠 Problem: {repair[3]}\n"
        f"💰 Price: {repair[4]:,} AMD\n"
        f"📌 Status: {repair[5]}"
    )


# ADD REPAIR

@router.message(Command("add"))
async def add_repair_command(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RepairForm.customer_name)

    await message.answer(
        "➕ NEW REPAIR ORDER\n\n"
        "Enter the customer's name:"
    )


@router.message(
    RepairForm.customer_name,
    F.text & ~F.text.startswith("/")
)
async def get_customer_name(message: Message, state: FSMContext):
    name = message.text.strip()

    if not name or len(name) > MAX_NAME_LENGTH:
        await message.answer(
            f"Please enter a name between 1 and {MAX_NAME_LENGTH} characters."
        )
        return

    await state.update_data(customer_name=name)
    await state.set_state(RepairForm.device)

    await message.answer("📱 Enter the device name:")


@router.message(
    RepairForm.device,
    F.text & ~F.text.startswith("/")
)
async def get_device(message: Message, state: FSMContext):
    device = message.text.strip()

    if not device or len(device) > MAX_DEVICE_LENGTH:
        await message.answer(
            f"Please enter a device name between 1 and {MAX_DEVICE_LENGTH} characters."
        )
        return

    await state.update_data(device=device)
    await state.set_state(RepairForm.problem)

    await message.answer("🛠 Describe the problem:")


@router.message(
    RepairForm.problem,
    F.text & ~F.text.startswith("/")
)
async def get_problem(message: Message, state: FSMContext):
    problem = message.text.strip()

    if not problem or len(problem) > MAX_PROBLEM_LENGTH:
        await message.answer(
            f"Please enter a description between 1 and {MAX_PROBLEM_LENGTH} characters."
        )
        return

    await state.update_data(problem=problem)
    await state.set_state(RepairForm.price)

    await message.answer("💰 Enter the repair price in AMD:")


@router.message(
    RepairForm.price,
    F.text & ~F.text.startswith("/")
)
async def get_price(message: Message, state: FSMContext):
    price_text = message.text.strip()

    if (
        not price_text.isdecimal()
        or len(price_text) > MAX_PRICE_LENGTH
    ):
        await message.answer(
            "❌ Please enter a valid positive price."
        )
        return

    price = int(price_text)

    if price <= 0:
        await message.answer(
            "Price must be greater than zero."
        )
        return

    data = await state.get_data()

    try:
        repair_id = db_add_repair(
            customer_name=data["customer_name"],
            device=data["device"],
            problem=data["problem"],
            price=price,
            user_id=message.from_user.id
        )
    except ValueError as error:
        await message.answer(f"❌ {error}\nPlease try again.")
        return

    await state.clear()

    repair = get_repair_by_id(
        repair_id,
        message.from_user.id
    )

    if not repair:
        await message.answer(
            "Repair was created, but could not be loaded.",
            reply_markup=get_back_keyboard()
        )
        return

    await message.answer(
        "✅ REPAIR SUCCESSFULLY CREATED!\n\n"
        + format_repair(repair),
        reply_markup=get_back_keyboard()
    )


# LIST REPAIRS

@router.message(Command("list"))
async def list_repairs_command(message: Message):
    repairs = get_all_repairs(message.from_user.id)

    if not repairs:
        await message.answer(
            "📋 No repair orders found.",
            reply_markup=get_back_keyboard()
        )
        return

    for repair in repairs:
        await message.answer(
            format_repair(repair),
            reply_markup=get_back_keyboard()
        )


# VIEW REPAIR

@router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery):
    try:
        _, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer("Repair not found.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Edit",
                    callback_data=f"edit_order:{repair_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="📌 Change Status",
                    callback_data=f"status_menu:{repair_id}:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Delete",
                    callback_data=f"delete_order:{repair_id}:{user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Back to Menu",
                    callback_data="back_to_menu"
                )
            ]
        ]
    )

    await callback.message.answer(
        format_repair(repair),
        reply_markup=keyboard
    )

    await callback.answer()


# EDIT REPAIR

@router.message(Command("edit"))
async def edit_command(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "To edit a repair, open All Repairs and press Edit."
    )


@router.callback_query(F.data.startswith("edit_order:"))
async def edit_order(callback: CallbackQuery, state: FSMContext):
    try:
        _, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer("Repair not found.", show_alert=True)
        return

    await state.clear()
    await state.update_data(repair_id=repair_id)

    await callback.message.answer(
        f"✏️ EDIT REPAIR #{repair_id}\n\n"
        "Choose the information you want to change:",
        reply_markup=get_edit_keyboard(repair_id, callback.from_user.id)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    try:
        _, field, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    allowed_fields = {
        "customer_name",
        "device",
        "problem",
        "price"
    }

    if field not in allowed_fields:
        await callback.answer("Invalid field.", show_alert=True)
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer("Repair not found.", show_alert=True)
        return

    await state.update_data(
        repair_id=repair_id,
        edit_field=field
    )

    await state.set_state(EditRepairForm.new_value)

    field_names = {
        "customer_name": "customer name",
        "device": "device",
        "problem": "problem description",
        "price": "price"
    }

    await callback.message.answer(
        f"Enter the new {field_names[field]}:"
    )

    await callback.answer()


@router.message(
    EditRepairForm.new_value,
    F.text & ~F.text.startswith("/")
)
async def save_edit(message: Message, state: FSMContext):
    new_value = message.text.strip()

    if not new_value:
        await message.answer("Please enter a valid value.")
        return

    data = await state.get_data()

    repair_id = data.get("repair_id")
    field = data.get("edit_field")

    if not repair_id or not field:
        await state.clear()
        await message.answer(
            "❌ Editing session expired. Please try again.",
            reply_markup=get_back_keyboard()
        )
        return

    if field == "customer_name" and len(new_value) > MAX_NAME_LENGTH:
        await message.answer(
            f"Name cannot exceed {MAX_NAME_LENGTH} characters."
        )
        return

    if field == "device" and len(new_value) > MAX_DEVICE_LENGTH:
        await message.answer(
            f"Device name cannot exceed {MAX_DEVICE_LENGTH} characters."
        )
        return

    if field == "problem" and len(new_value) > MAX_PROBLEM_LENGTH:
        await message.answer(
            f"Description cannot exceed {MAX_PROBLEM_LENGTH} characters."
        )
        return

    if field == "price":
        if (
            not new_value.isdecimal()
            or len(new_value) > MAX_PRICE_LENGTH
            or int(new_value) <= 0
        ):
            await message.answer(
                "❌ Price must be a positive number. Try again:"
            )
            return

        new_value = int(new_value)

    try:
        success = update_repair(
            repair_id,
            field,
            new_value,
            message.from_user.id
        )
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    await state.clear()

    if success:
        repair = get_repair_by_id(
            repair_id,
            message.from_user.id
        )

        if repair:
            await message.answer(
                "✅ REPAIR UPDATED SUCCESSFULLY!\n\n"
                + format_repair(repair),
                reply_markup=get_back_keyboard()
            )
        else:
            await message.answer(
                "Repair updated, but could not be loaded.",
                reply_markup=get_back_keyboard()
            )
    else:
        await message.answer(
            "❌ Could not update the repair.",
            reply_markup=get_back_keyboard()
        )


# CHANGE STATUS

@router.message(Command("status"))
async def status_command(message: Message):
    await message.answer(
        "To change a repair status, open All Repairs, "
        "press View, then Change Status."
    )


@router.callback_query(F.data.startswith("status_menu:"))
async def status_menu(callback: CallbackQuery):
    try:
        _, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer("Repair not found.", show_alert=True)
        return

    await callback.message.answer(
        f"📌 Choose a new status for Repair #{repair_id}:",
        reply_markup=get_status_keyboard(repair_id, callback.from_user.id)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("status_set:"))
async def set_repair_status(callback: CallbackQuery):
    try:
        _, repair_id, new_status, user_id = callback.data.split(":", 3)
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    if new_status not in VALID_STATUSES:
        await callback.answer("Invalid status.", show_alert=True)
        return

    try:
        success = update_repair(
            repair_id,
            "status",
            new_status,
            callback.from_user.id
        )
    except ValueError:
        await callback.answer(
            "Could not update the status.",
            show_alert=True
        )
        return

    if not success:
        await callback.answer("Repair not found.", show_alert=True)
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer(
            "Repair could not be loaded.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "✅ STATUS UPDATED!\n\n" + format_repair(repair),
        reply_markup=get_back_keyboard()
    )

    await callback.answer("Status updated!")


# DELETE REPAIR

@router.message(Command("delete"))
async def delete_command(message: Message):
    await message.answer(
        "To delete a repair, open All Repairs and press Delete."
    )


@router.callback_query(F.data.startswith("delete_order:"))
async def delete_order(callback: CallbackQuery):
    try:
        _, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    repair = get_repair_by_id(repair_id, callback.from_user.id)

    if not repair:
        await callback.answer("Repair not found.", show_alert=True)
        return

    await callback.message.answer(
        f"⚠️ Are you sure you want to delete Repair #{repair_id}?\n\n"
        "This action cannot be undone.",
        reply_markup=get_delete_keyboard(repair_id, callback.from_user.id)
    )

    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def delete_confirm(callback: CallbackQuery):
    try:
        _, repair_id, user_id = callback.data.split(":")
        repair_id = int(repair_id)
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    success = db_delete_repair(
        repair_id,
        callback.from_user.id
    )

    if success:
        await callback.message.edit_text(
            f"✅ Repair #{repair_id} has been deleted.",
            reply_markup=get_back_keyboard()
        )

        await callback.answer("Deleted successfully!")
    else:
        await callback.answer("Repair not found.", show_alert=True)


@router.callback_query(F.data.startswith("delete_cancel:"))
async def delete_cancel(callback: CallbackQuery):
    try:
        _, user_id = callback.data.split(":")
        user_id = int(user_id)
    except (ValueError, TypeError):
        await callback.answer("Invalid request.", show_alert=True)
        return

    if callback.from_user.id != user_id:
        await callback.answer(
            "This button is not for you.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "❌ Deletion cancelled.",
        reply_markup=get_back_keyboard()
    )

    await callback.answer()


# CANCEL CURRENT ACTION

@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "❌ Current action cancelled.",
        reply_markup=get_back_keyboard()
    )
