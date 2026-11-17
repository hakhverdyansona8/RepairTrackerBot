import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, Message
from aiogram.filters import CommandStart, Command

from config import BOT_TOKEN, ADMIN_ID, is_admin
from database import (
    init_db,
    migrate_json,
    assign_legacy_repairs,
    register_user
)
from handlers.admin import router as admin_router
from handlers.repairs import router as repairs_router
from handlers.menu import router as menu_router, get_main_menu


dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(repairs_router)
dp.include_router(menu_router)


@dp.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if is_admin(user.id):
        welcome_text = (
            "🔧 REPAIR TRACKER\n\n"
            "Welcome, Admin!\n\n"
            "Choose an action from the dashboard:"
        )
    else:
        welcome_text = (
            "🔧 REPAIR TRACKER\n\n"
            "Welcome to your personal repair management system!\n\n"
            "Your repair orders are private.\n\n"
            "Choose an action from the dashboard:"
        )

    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(user.id)
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "🔧 REPAIR TRACKER — HELP\n\n"
        "Use the Dashboard buttons to manage your repair orders.\n\n"
        "/start — Open Dashboard\n"
        "/menu — Open Dashboard\n"
        "/admin — Open Admin Panel\n"
        "/help — Show help\n\n"
        "Each user has their own private repair orders."
    )


async def main():
    init_db()
    migrate_json()
    assign_legacy_repairs(ADMIN_ID)

    async with Bot(token=BOT_TOKEN) as bot:
        await bot.set_my_commands([
            BotCommand(
                command="start",
                description="Open Dashboard"
            ),
            BotCommand(
                command="menu",
                description="Open Dashboard"
            ),
            BotCommand(
                command="admin",
                description="Open Admin Panel"
            ),
            BotCommand(
                command="help",
                description="Show help"
            )
        ])

        print("Database initialized successfully!")
        print("Repair Tracker Bot is running...")

        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
