import os
import json
import ast
import operator
import asyncio
from datetime import datetime
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 6823061366

USERS_FILE = "users.json"
AUTO_REPLY = True


# =========================
# USERS
# =========================

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Could not load users:", e)
        return {}


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Could not save users:", e)


users = load_users()


def register_user(user):
    if not user:
        return

    user_id = str(user.id)

    users[user_id] = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_seen": datetime.now().isoformat(),
    }

    save_users(users)


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    keyboard = [
        [
            InlineKeyboardButton("🆔 آیدی من", callback_data="myid"),
            InlineKeyboardButton("ℹ️ اطلاعات من", callback_data="info"),
        ],
        [
            InlineKeyboardButton("🏓 پینگ", callback_data="ping"),
            InlineKeyboardButton("🕐 ساعت", callback_data="time"),
        ],
        [
            InlineKeyboardButton("📖 راهنما", callback_data="help"),
        ],
    ]

    await update.message.reply_text(
        "درود! 👋🔥\n"
        "ربات روشنه و آماده‌ست.\n\n"
        "از دکمه‌های زیر استفاده کن یا /help بزن.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# /HELP
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    text = (
        "📖 *راهنمای ربات*\n\n"
        "/start — شروع ربات\n"
        "/help — راهنما\n"
        "/id — نمایش آیدی عددی\n"
        "/info — اطلاعات کاربر\n"
        "/ping — تست اتصال\n"
        "/time — نمایش ساعت\n"
        "/echo متن — تکرار متن\n"
        "/calc عبارت — محاسبه\n"
    )

    if update.effective_user.id == OWNER_ID:
        text += (
            "\n👑 *دستورات مالک:*\n"
            "/stats — آمار کاربران\n"
            "/users — تعداد کاربران\n"
            "/broadcast متن — ارسال به کاربران\n"
            "/autoreply on/off — روشن/خاموش کردن پاسخ خودکار\n"
        )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
    )


# =========================
# /ID
# =========================

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    await update.message.reply_text(
        f"🆔 آیدی عددی شما:\n`{update.effective_user.id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# =========================
# /INFO
# =========================

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    user = update.effective_user
    username = f"@{user.username}" if user.username else "ندارد"

    await update.message.reply_text(
        f"ℹ️ *اطلاعات شما*\n\n"
        f"👤 نام: {user.first_name}\n"
        f"🔗 یوزرنیم: {username}\n"
        f"🆔 ID: `{user.id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# =========================
# /PING
# =========================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    await update.message.reply_text(
        "🏓 Pong!\nربات سالمه 🔥"
    )


# =========================
# /TIME
# =========================

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    now = datetime.now().strftime("%H:%M:%S")

    await update.message.reply_text(
        f"🕐 ساعت فعلی:\n`{now}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# =========================
# /ECHO
# =========================

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    if not context.args:
        await update.message.reply_text(
            "مثال:\n`/echo سلام داداش`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.reply_text(
        " ".join(context.args)
    )


# =========================
# CALCULATOR
# =========================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_calculate(expression):

    def calculate(node):

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError()

        if isinstance(node, ast.UnaryOp):
            op = ALLOWED_OPERATORS.get(type(node.op))

            if not op:
                raise ValueError()

            return op(calculate(node.operand))

        if isinstance(node, ast.BinOp):
            op = ALLOWED_OPERATORS.get(type(node.op))

            if not op:
                raise ValueError()

            return op(
                calculate(node.left),
                calculate(node.right),
            )

        raise ValueError()

    tree = ast.parse(expression, mode="eval")

    return calculate(tree.body)


async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)

    if not context.args:
        await update.message.reply_text(
            "مثال:\n`/calc 10+5*2`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:

        result = safe_calculate(
            " ".join(context.args)
        )

        await update.message.reply_text(
            f"🧮 نتیجه:\n`{result}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception:

        await update.message.reply_text(
            "❌ عبارت ریاضی معتبر نیست."
        )


# =========================
# BUTTONS
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    register_user(user)

    if query.data == "myid":

        await query.message.reply_text(
            f"🆔 آیدی شما:\n`{user.id}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif query.data == "info":

        username = (
            f"@{user.username}"
            if user.username
            else "ندارد"
        )

        await query.message.reply_text(
            f"👤 نام: {user.first_name}\n"
            f"🔗 یوزرنیم: {username}\n"
            f"🆔 ID: `{user.id}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif query.data == "ping":

        await query.message.reply_text(
            "🏓 Pong! 🔥"
        )

    elif query.data == "time":

        now = datetime.now().strftime("%H:%M:%S")

        await query.message.reply_text(
            f"🕐 ساعت: `{now}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif query.data == "help":

        await query.message.reply_text(
            "📖 دستورات:\n\n"
            "/start\n"
            "/help\n"
            "/id\n"
            "/info\n"
            "/ping\n"
            "/time\n"
            "/echo\n"
            "/calc"
        )


# =========================
# AUTO REPLY
# =========================

async def auto_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    register_user(update.effective_user)

    if not AUTO_REPLY:
        return

    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()

    replies = {

        "سلام":
            "سلام داداش 😂❤️",

        "خوبی":
            "آره داداش، مرسی 😎🔥",

        "چطوری":
            "عالی‌ام 😎🔥",

        "هلو":
            "هلووو 😂",

    }

    if text in replies:

        await update.message.reply_text(
            replies[text]
        )


# =========================
# OWNER CHECK
# =========================

def is_owner(update):

    return (
        update.effective_user
        and update.effective_user.id == OWNER_ID
    )


# =========================
# /STATS
# =========================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ دسترسی نداری."
        )

        return

    await update.message.reply_text(
        f"👑 تعداد کاربران ثبت‌شده: {len(users)}"
    )


# =========================
# /USERS
# =========================

async def users_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ دسترسی نداری."
        )

        return

    await update.message.reply_text(
        f"👥 تعداد کاربران: {len(users)}"
    )


# =========================
# /BROADCAST
# =========================

async def broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ دسترسی نداری."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "مثال:\n"
            "/broadcast سلام به همه"
        )

        return

    message = " ".join(context.args)

    sent = 0
    failed = 0

    for user_id in list(users.keys()):

        try:

            await context.bot.send_message(
                chat_id=int(user_id),
                text=message,
            )

            sent += 1

            # جلوگیری از فشار زیاد روی Telegram API
            await asyncio.sleep(0.05)

        except Exception:

            failed += 1

    await update.message.reply_text(
        f"📨 ارسال تمام شد.\n\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}"
    )


# =========================
# /AUTOREPLY
# =========================

async def autoreply_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global AUTO_REPLY

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ دسترسی نداری."
        )

        return

    if not context.args:

        status = (
            "روشن 🟢"
            if AUTO_REPLY
            else "خاموش 🔴"
        )

        await update.message.reply_text(
            f"وضعیت پاسخ خودکار: {status}\n\n"
            "/autoreply on\n"
            "/autoreply off"
        )

        return

    option = context.args[0].lower()

    if option == "on":

        AUTO_REPLY = True

        await update.message.reply_text(
            "✅ پاسخ خودکار روشن شد."
        )

    elif option == "off":

        AUTO_REPLY = False

        await update.message.reply_text(
            "🔴 پاسخ خودکار خاموش شد."
        )

    else:

        await update.message.reply_text(
            "فقط `on` یا `off` بنویس.",
            parse_mode=ParseMode.MARKDOWN,
        )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "ERROR:",
        repr(context.error)
    )


# =========================
# MAIN
# =========================
# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(b"Bot is alive")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server():

    port = int(os.getenv("PORT", "10000"))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Health server running on port {port}")

    server.serve_forever()
def main():

    if not TOKEN:

        print(
            "ERROR: BOT_TOKEN is not set."
        )

        return
    threading.Thread(
        target=start_health_server,
        daemon=True
    ).start()
    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        CommandHandler("id", get_id)
    )

    app.add_handler(
        CommandHandler("info", info)
    )

    app.add_handler(
        CommandHandler("ping", ping)
    )

    app.add_handler(
        CommandHandler("time", time_command)
    )

    app.add_handler(
        CommandHandler("echo", echo)
    )

    app.add_handler(
        CommandHandler("calc", calc)
    )

    # Buttons
    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    # Owner commands
    app.add_handler(
        CommandHandler("stats", stats)
    )

    app.add_handler(
        CommandHandler("users", users_command)
    )

    app.add_handler(
        CommandHandler("broadcast", broadcast)
    )

    app.add_handler(
        CommandHandler("autoreply", autoreply_command)
    )

    # Normal messages
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            auto_reply
        )
    )

    # Error handler
    app.add_error_handler(
        error_handler
    )

    print("Bot is running...")

    app.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
