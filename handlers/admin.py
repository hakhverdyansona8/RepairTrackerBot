from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

from config import is_admin
from database import get_all_users, get_admin_statistics


router = Router()


def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="admin:stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Users",
                    callback_data="admin:users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="admin:panel"
                )
            ]
        ]
    )


def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Back",
                    callback_data="admin:panel"
                )
            ]
        ]
    )


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    await message.answer(
        "🔐 ADMIN PANEL\n\n"
        "Welcome to the administration dashboard.\n\n"
        "Choose an action:",
        reply_markup=get_admin_keyboard()
    )


@router.callback_query(F.data == "admin:panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied!",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "🔐 ADMIN PANEL\n\n"
        "Choose an action:",
        reply_markup=get_admin_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_statistics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied!",
            show_alert=True
        )
        return

    stats = get_admin_statistics()

    text = (
        "📊 SYSTEM STATISTICS\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"🔧 Total repairs: {stats['total_repairs']}\n\n"
        "📌 REPAIR STATUS\n"
        f"🟡 Pending: {stats['pending']}\n"
        f"🔵 In Progress: {stats['in_progress']}\n"
        f"🟢 Completed: {stats['completed']}\n\n"
        f"💰 Total order value: "
        f"{stats['total_revenue']:,} AMD"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied!",
            show_alert=True
        )
        return

    users = get_all_users()

    if not users:
        text = "👥 No registered users yet."
    else:
        lines = ["👥 REGISTERED USERS\n"]

        for index, user in enumerate(users[:10], start=1):
            (
                telegram_id,
                username,
                first_name,
                last_name,
                repair_count
            ) = user

            full_name = " ".join(
                name
                for name in (first_name, last_name)
                if name
            ) or "Unknown"

            username_text = (
                f"@{username}"
                if username
                else "No username"
            )

            lines.append(
                f"{index}. {full_name}\n"
                f"   {username_text}\n"
                f"   ID: {telegram_id}\n"
                f"   Repairs: {repair_count}\n"
            )

        if len(users) > 10:
            lines.append(
                f"Showing 10 of {len(users)} users."
            )

        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard()
    )

    await callback.answer()
