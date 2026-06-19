# SmartTo-DoList

**SmartTo-DoList** is a modern and lightweight web application for task management, built with Flask. It is tightly integrated with a Telegram bot for convenient reminders and on-the-go task management.

## 🚀 Key Features

- **Full Task Management**: Create, edit, delete, filter, and search for tasks.
- **Priorities and Categories**: Organize your tasks for better focus.
- **Smart Time Input**: Use natural language to set deadlines (e.g., "tomorrow at 10", "in 2 hours").
- **Telegram Integration**: Receive reminders and manage tasks directly from the messenger.
- **Responsive Design**: User-friendly on both desktop and mobile devices.
- **Light and Dark Themes**: Customize the appearance to your liking.
- **Timezone Support**: Set your timezone in the settings for correct reminder functionality.

## 🛠️ Tech Stack

- **Backend**: Flask, SQLAlchemy, Gunicorn
- **Database**: PostgreSQL (recommended), SQLite (for development)
- **Frontend**: HTML, CSS, plain JavaScript (no frameworks)
- **Bot**: pyTelegramBotAPI

## ⚙️ Quick Start (Local Development)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/fert1z/SmartTo-DoList.git
    cd SmartTo-DoList
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS / Linux
    # .venv\Scripts\activate  # Windows
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Copy the example file and edit it:
    ```bash
    cp .env.example .env
    ```
    - Set a `SECRET_KEY` (can be any random string).
    - To run the Telegram bot locally, add `TELEGRAM_BOT_TOKEN`.

5.  **Initialize the database:**
    ```bash
    export FLASK_APP=wsgi.py
    flask init-database
    ```

6.  **Run the web server and bot:**
    The `start.sh` script will automatically run both the website and the Telegram bot (if a token is provided).
    ```bash
    chmod +x start.sh
    ./start.sh
    ```
    The application will be available at `http://127.0.0.1:10000`.

## ☁️ Deployment on Render (Recommended Method)

This project is ideal for Render's free tier. We will deploy it as 3 independent services connected to a single environment group.

### Step 1: Create an Environment Group

1.  In the Render dashboard, go to **Environment Groups** and click **New Environment Group**.
2.  Name it (e.g., `smart-todolist-env`).
3.  Add the following variables:
    - `DATABASE_URL`: Will be available after creating the database (see Step 2).
    - `SECRET_KEY`: Your unique secret string.
    - `TELEGRAM_BOT_TOKEN`: Your Telegram bot's token.
    - `PYTHON_VERSION`: `3.11` (or any other supported version).

### Step 2: Create a Database

1.  In the Render dashboard, click **New +** → **PostgreSQL**.
2.  Choose a name and select the free tier.
3.  After the database is created, go to its settings, copy the **Internal Database URL**, and paste it as the value for `DATABASE_URL` in your environment group.

### Step 3: Deploy the Web Service

1.  Click **New +** → **Web Service**.
2.  Connect your GitHub repository.
3.  Configure the service:
    - **Name**: `smart-todolist-web` (or any other name).
    - **Environment**: Select your `smart-todolist-env` group.
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `gunicorn wsgi:app`
4.  Click **Create Web Service**.

### Step 4: Deploy the Telegram Bot

1.  Click **New +** → **Background Worker**.
2.  Connect the same GitHub repository.
3.  Configure the worker:
    - **Name**: `smart-todolist-bot`.
    - **Environment**: Select your `smart-todolist-env` group.
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: `python -m tg_bot.run`
4.  Click **Create Background Worker**.

### Step 5: Initialize the Database

1.  Wait for the **Web Service** to have a `Live` status.
2.  Go to its **Shell** tab.
3.  Execute the command: `flask init-database`

After this, your website and bot will run independently and stably, using a single shared database.

## 🗂 Project Structure

- `app/`: Main Flask application code (routes, models, templates).
- `tg_bot/`: Telegram bot logic.
- `start.sh`: Script for **local** startup of the site and bot.
- `wsgi.py`: WSGI entry point for Gunicorn.
- `requirements.txt`: List of dependencies.
- `tests/`: Automatic tests.
