# Repair Tracker Bot

A Telegram-based repair order management system developed with Python and aiogram 3.

The bot allows users to manage repair orders, track their status, and monitor order statistics through a simple Telegram interface.

## Features

- Create, view, edit, and delete repair orders
- Search orders by ID
- Track repair statuses: Pending, In Progress, Completed
- Individual user accounts and private order records
- Personal order statistics
- Admin panel with user management and system statistics

## Tech Stack

- **Python** — application logic
- **aiogram 3** — Telegram Bot API
- **SQLite** — database management
- **python-dotenv** — environment configuration

## Project Structure

```text
RepairTrackerBot/
├── handlers/
│   ├── admin.py
│   ├── menu.py
│   └── repairs.py
├── bot.py
├── config.py
├── database.py
├── requirements.txt
└── .gitignore
```

## Installation

```bash
git clone YOUR_REPOSITORY_URL
cd RepairTrackerBot

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
```

Run the application:

```bash
python bot.py
```

## Security

- Credentials are stored in environment variables.
- Repair records are associated with individual Telegram user IDs.
- Database queries use parameterized SQL statements.
- Local database and configuration files are excluded from version control.

---

**Developed as a personal Python project.**