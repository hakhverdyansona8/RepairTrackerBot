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

from config import is_admin
from database import get_all_repairs, get_repair_by_id
from handlers.repairs import RepairForm, format_repair


router = Router()


class SearchRepairForm(StatesGroup):
    repair_id = State()


# MAIN DASHBOARD

def get_main_menu(user_id=None):
    keyboard = [
        [
            InlineKeyboardButton(
                text="➕ Add Repair",
                callback_data="menu_add"
            ),
            InlineKeyboardButton(
                text="📋 All Repairs",
                callback_data="menu_list"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔍 Search Repair",
                callback_data="menu_search"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Statistics",
                callback_data="menu_stats"
            ),
            InlineKeyboardButton(
                text="💰 Revenue",
                callback_data="menu_revenue"
            )
        ]
    ]

    if user_id is not None and is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton(
                text="🔐 Admin Panel",
                callback_data="admin:panel"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# BACK TO MENU

def get_back_menu():
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


# REPAIR KEYBOARD

def get_repair_keyboard(repair_id, user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👁 View",
                    callback_data=f"view_order:{repair_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="✏️ Edit",
                    callback_data=f"edit_order:{repair_id}:{user_id}"
                ),
                InlineKeyboardButton(
                    text="🗑 Delete",
                    callback_data=f"delete_order:{repair_id}:{user_id}"
                )
            ]
        ]
    )


# SHOW MENU

@router.message(Command("menu"))
async def show_menu(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "🔧 REPAIR TRACKER DASHBOARD\n\n"
        "Welcome to your personal repair management system!\n"
        "Your orders are private.\n\n"
        "Choose an action:",
        reply_markup=get_main_menu(message.from_user.id)
    )


# BACK TO MENU

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "🔧 REPAIR TRACKER DASHBOARD\n\n"
        "Choose an action:",
        reply_markup=get_main_menu(callback.from_user.id)
    )

    await callback.answer()


# ADD REPAIR

@router.callback_query(F.data == "menu_add")
async def menu_add(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(RepairForm.customer_name)

    await callback.message.answer(
        "➕ NEW REPAIR ORDER\n\n"
        "Enter the customer's name:"
    )

    await callback.answer()


# ALL REPAIRS

@router.callback_query(F.data == "menu_list")
async def menu_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    repairs = get_all_repairs(user_id)

    if not repairs:
        await callback.message.answer(
            "📋 No repair orders found.",
            reply_markup=get_back_menu()
        )
    else:
        await callback.message.answer(
            f"📋 ALL YOUR REPAIRS\n\n"
            f"Total orders: {len(repairs)}"
        )

        for repair in repairs:
            await callback.message.answer(
                format_repair(repair),
                reply_markup=get_repair_keyboard(
                    repair[0],
                    user_id
                )
            )

        await callback.message.answer(
            "Choose another action:",
            reply_markup=get_back_menu()
        )

    await callback.answer()


# SEARCH REPAIR

@router.callback_query(F.data == "menu_search")
async def menu_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SearchRepairForm.repair_id)

    await callback.message.answer(
        "🔍 SEARCH REPAIR\n\n"
        "Enter the repair ID:"
    )

    await callback.answer()


@router.message(
    SearchRepairForm.repair_id,
    F.text & ~F.text.startswith("/")
)
async def search_repair(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "❌ Please enter a valid numeric ID."
        )
        return

    repair_id = int(message.text)

    repair = get_repair_by_id(
        repair_id,
        message.from_user.id
    )

    await state.clear()

    if not repair:
        await message.answer(
            f"❌ Repair #{repair_id} was not found.",
            reply_markup=get_back_menu()
        )
        return

    await message.answer(
        format_repair(repair),
        reply_markup=get_repair_keyboard(
            repair_id,
            message.from_user.id
        )
    )

    await message.answer(
        "Choose another action:",
        reply_markup=get_back_menu()
    )


# STATISTICS

@router.callback_query(F.data == "menu_stats")
async def menu_stats(callback: CallbackQuery):
    repairs = get_all_repairs(callback.from_user.id)

    total = len(repairs)

    pending = sum(
        1 for repair in repairs
        if repair[5] == "Pending"
    )

    in_progress = sum(
        1 for repair in repairs
        if repair[5] == "In Progress"
    )

    completed = sum(
        1 for repair in repairs
        if repair[5] == "Completed"
    )

    await callback.message.answer(
        "📊 YOUR REPAIR STATISTICS\n\n"
        f"📦 Total Orders: {total}\n"
        f"⏳ Pending: {pending}\n"
        f"🔧 In Progress: {in_progress}\n"
        f"✅ Completed: {completed}",
        reply_markup=get_back_menu()
    )

    await callback.answer()


# REVENUE

@router.callback_query(F.data == "menu_revenue")
async def menu_revenue(callback: CallbackQuery):
    repairs = get_all_repairs(callback.from_user.id)

    total_value = sum(
        repair[4] for repair in repairs
    )

    completed_value = sum(
        repair[4] for repair in repairs
        if repair[5] == "Completed"
    )

    await callback.message.answer(
        "💰 REPAIR VALUE REPORT\n\n"
        f"Total Order Value: {total_value:,} AMD\n"
        f"Completed Order Value: {completed_value:,} AMD",
        reply_markup=get_back_menu()
    )

    await callback.answer()
