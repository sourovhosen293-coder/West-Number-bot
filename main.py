import os
import re
import random
import sqlite3
import asyncio
from datetime import datetime

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

# ============================================================
#                    SECRET NUMBER BOT
#                         main.py
# ============================================================

# =========================
# BOT CONFIG
# =========================

BOT_TOKEN = "8875251875:AAG_UmQZsl8bfHMmR8DGM-kZ1dN0ITgzB84"

# এখানে আপনার Telegram ID বসাবেন
# একাধিক Admin হলে:
# ADMIN_IDS = [123456789, 987654321]
ADMIN_IDS = [5747820322]

MIN_WITHDRAW = 30

DB_NAME = "secret_number.db"


# ============================================================
#                    CUSTOM EMOJI IDs
# ============================================================

EMOJI = {

    # My Stats
    "username": "6152280926257684465",
    "telegram_id": "6086867401803532902",
    "subscription": "6104644116832853064",
    "subscription_price": "6084695716024821348",
    "duration": "6107109342161411278",
    "total_earning": "6105092867900840631",
    "balance": "6190336264940559752",

    # Subscription
    "active": "6087027281971127830",
    "inactive": "6206448624298104566",

    # Services
    "facebook": "6091599390621834528",
    "instagram": "5319160079465857105",
    "whatsapp": "6298323188849838091",
    "telegram": "6242460902872850889",
    "paypal": "6258109564676220200",
}


# ============================================================
#                         SERVICES
# ============================================================

SERVICES = {

    "facebook": {
        "name": "Facebook",
        "emoji": EMOJI["facebook"],
        "button": "📘 Facebook",
    },

    "instagram": {
        "name": "Instagram",
        "emoji": EMOJI["instagram"],
        "button": "📸 Instagram",
    },

    "whatsapp": {
        "name": "WhatsApp",
        "emoji": EMOJI["whatsapp"],
        "button": "🟢 WhatsApp",
    },

    "telegram": {
        "name": "Telegram",
        "emoji": EMOJI["telegram"],
        "button": "✈️ Telegram",
    },

    "paypal": {
        "name": "Paypal",
        "emoji": EMOJI["paypal"],
        "button": "💳 Paypal",
    },

    "tiktok": {
        "name": "TikTok",
        "emoji": None,
        "button": "🎵 TikTok",
    },

    "imo": {
        "name": "IMO",
        "emoji": None,
        "button": "💬 IMO",
    },
}


# Aliases
ALIASES = {
    "fb": "facebook",
    "facebook": "facebook",

    "int": "instagram",
    "ig": "instagram",
    "instagram": "instagram",
    "intagram": "instagram",

    "ws": "whatsapp",
    "wa": "whatsapp",
    "whatsapp": "whatsapp",

    "tg": "telegram",
    "telegram": "telegram",

    "py": "paypal",
    "paypal": "paypal",

    "tt": "tiktok",
    "tiktok": "tiktok",

    "imo": "imo",
}


# ============================================================
#                         DATABASE
# ============================================================

db = sqlite3.connect(DB_NAME, check_same_thread=False)
db.row_factory = sqlite3.Row


def database():

    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',

            banned INTEGER DEFAULT 0,

            subscription INTEGER DEFAULT 0,
            subscription_price TEXT DEFAULT '0$',
            duration TEXT DEFAULT '30DAY',

            total_earning TEXT DEFAULT '0$',
            balance REAL DEFAULT 0,

            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            service TEXT PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT,
            country TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT
        )
    """)

    for service in SERVICES:

        cursor.execute(
            """
            INSERT OR IGNORE INTO services
            (service, enabled)
            VALUES (?, 1)
            """,
            (service,)
        )

    db.commit()


database()


# ============================================================
#                         HELPERS
# ============================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS


def ensure_user(user):

    db.execute(
        """
        INSERT INTO users
        (user_id, username, first_name, created_at)

        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name
        """,

        (
            user.id,
            user.username or "",
            user.first_name or "",
            datetime.now().isoformat(),
        )
    )

    db.commit()


def get_user(user_id):

    return db.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()


def custom_emoji(emoji_id, fallback):

    if not emoji_id:
        return fallback

    return f'<tg-emoji emoji-id="{emoji_id}">⭐</tg-emoji>'


def service_name(service):

    return SERVICES[service]["name"]


def service_emoji(service):

    data = SERVICES[service]

    if data["emoji"]:
        return custom_emoji(
            data["emoji"],
            data["button"].split()[0]
        )

    return data["button"].split()[0]


def active_services():

    rows = db.execute(
        """
        SELECT service
        FROM services
        WHERE enabled=1
        ORDER BY rowid
        """
    ).fetchall()

    return [row["service"] for row in rows]


def get_countries(service):

    return db.execute(
        """
        SELECT *
        FROM countries
        WHERE service=?
        ORDER BY id
        """,
        (service,)
    ).fetchall()


# ============================================================
#                         MAIN MENU
# ============================================================

def main_menu(user_id):

    buttons = [

        [
            InlineKeyboardButton(
                "📱 Get Number",
                callback_data="get_number"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 My Stats",
                callback_data="stats"
            )
        ],

        [
            InlineKeyboardButton(
                "💸 Withdrawal",
                callback_data="withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "🆘 Support",
                callback_data="support"
            )
        ],
    ]

    # Admin only
    if is_admin(user_id):

        buttons.append(
            [
                InlineKeyboardButton(
                    "⚙️ Admin Panel",
                    callback_data="admin"
                )
            ]
        )

    return InlineKeyboardMarkup(buttons)


# ============================================================
#                         /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    ensure_user(user)

    row = get_user(user.id)

    if row["banned"]:

        await update.message.reply_text(
            "🚫 <b>You are banned from this bot.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    await update.message.reply_text(

        "╔══════════════════════╗\n"
        "       <b>SECRET NUMBER BOT</b>\n"
        "╚══════════════════════╝\n\n"

        "🌟 Welcome!\n"
        "Select an option below:",

        parse_mode=ParseMode.HTML,

        reply_markup=main_menu(user.id)
    )


# ============================================================
#                       GET NUMBER
# ============================================================

async def get_number_page(query):

    buttons = []

    for service in active_services():

        buttons.append(
            [
                InlineKeyboardButton(
                    SERVICES[service]["button"],
                    callback_data=f"service:{service}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    )

    await query.edit_message_text(

        "📍 <b>Select a service:</b>\n\n"
        "Choose the service you want.",

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ============================================================
#                     SERVICE COUNTRIES
# ============================================================

async def service_page(query, service):

    buttons = []

    countries = get_countries(service)

    for country in countries:

        buttons.append(
            [
                InlineKeyboardButton(
                    country["country"],
                    callback_data=f"country:{country['id']}"
                )
            ]
        )

    if not buttons:

        buttons.append(
            [
                InlineKeyboardButton(
                    "⚠️ No Country Available",
                    callback_data="nothing"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="get_number"
            )
        ]
    )

    await query.edit_message_text(

        f"📍 <b>Select a country for "
        f"{service_emoji(service)} "
        f"{service_name(service)}:</b>",

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ============================================================
#                         MY STATS
# ============================================================

async def stats_page(query, user_id):

    user = get_user(user_id)

    if user["subscription"]:

        sub = (
            custom_emoji(
                EMOJI["active"],
                "🟢"
            )
            + " Active"
        )

    else:

        sub = (
            custom_emoji(
                EMOJI["inactive"],
                "🔴"
            )
            + " Detective"
        )

    username = user["username"]

    if username:

        username = "@" + username

    else:

        username = "N/A"

    text = (

        "╔══════════════════════╗\n"
        "          <b>MY STATS</b>\n"
        "╚══════════════════════╝\n\n"

        f"{custom_emoji(EMOJI['username'], '👤')} "
        f"<b>Username:</b> {username}\n\n"

        f"{custom_emoji(EMOJI['telegram_id'], '🆔')} "
        f"<b>Telegram ID:</b> <code>{user_id}</code>\n\n"

        f"{custom_emoji(EMOJI['subscription'], '📋')} "
        f"<b>My Subscription:</b> {sub}\n\n"

        f"{custom_emoji(EMOJI['subscription_price'], '💵')} "
        f"<b>Subscription Price:</b> "
        f"{user['subscription_price']}\n\n"

        f"{custom_emoji(EMOJI['duration'], '⏳')} "
        f"<b>Duration:</b> "
        f"{user['duration']}\n\n"

        f"{custom_emoji(EMOJI['total_earning'], '💰')} "
        f"<b>Total Earning:</b> "
        f"{user['total_earning']}\n\n"

        f"{custom_emoji(EMOJI['balance'], '💳')} "
        f"<b>My Balance:</b> "
        f"{user['balance']:.2f} Tk"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    ]

    await query.edit_message_text(

        text,

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
#                         WITHDRAW
# ============================================================

async def withdraw_page(query):

    keyboard = [

        [
            InlineKeyboardButton(
                "💳 Nagad",
                callback_data="withdraw:Nagad"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 Rocket",
                callback_data="withdraw:Rocket"
            )
        ],

        [
            InlineKeyboardButton(
                "💳 Binnace",
                callback_data="withdraw:Binance"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="home"
            )
        ]
    ]

    text = (

        "╔══════════════════════╗\n"
        "        <b>WITHDRAWAL</b>\n"
        "╚══════════════════════╝\n\n"

        "🔥 <b>Total Otp:</b> 0\n\n"

        "👥 <b>Total Reffer:</b> 0\n\n"

        "💰 <b>BALANCE:</b> 0 Tk\n\n"

        f"🔒 <b>MINIMUM:</b> {MIN_WITHDRAW} Tk\n\n"

        "<b>SELECT METHOD</b>"
    )

    await query.edit_message_text(

        text,

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
#                         SUPPORT
# ============================================================

async def support_page(query):

    rows = db.execute(
        "SELECT * FROM supports ORDER BY id"
    ).fetchall()

    buttons = []

    for row in rows:

        value = row["value"]

        if value.startswith("https://t.me/"):

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"🆘 {value}",
                        url=value
                    )
                ]
            )

        elif value.startswith("@"):

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"🆘 {value}",
                        url=f"https://t.me/{value[1:]}"
                    )
                ]
            )

        else:

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"🆘 {value}",
                        callback_data="support_info"
                    )
                ]
            )

    if not buttons:

        buttons.append(
            [
                InlineKeyboardButton(
                    "⚠️ Support not configured",
                    callback_data="nothing"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    )

    await query.edit_message_text(

        "🆘 <b>SUPPORT</b>\n\n"
        "Select a support contact:",

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ============================================================
#                         ADMIN PANEL
# ============================================================

async def admin_page(query):

    if not is_admin(query.from_user.id):

        await query.answer(
            "❌ Admin Only",
            show_alert=True
        )

        return

    keyboard = [

        [
            InlineKeyboardButton(
                "📢 Broadcast",
                callback_data="admin_broadcast"
            ),

            InlineKeyboardButton(
                "📊 Stats",
                callback_data="admin_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🆘 Support",
                callback_data="admin_support"
            ),

            InlineKeyboardButton(
                "🚫 Ban / Unban",
                callback_data="admin_ban"
            )
        ],

        [
            InlineKeyboardButton(
                "📱 Get Number",
                callback_data="admin_services"
            )
        ],

        [
            InlineKeyboardButton(
                "🌍 Country Manager",
                callback_data="admin_countries"
            )
        ],

        [
            InlineKeyboardButton(
                "👤 User Stats",
                callback_data="admin_userstats"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
            )
        ]
    ]

    await query.edit_message_text(

        "╔══════════════════════╗\n"
        "         <b>ADMIN PANEL</b>\n"
        "╚══════════════════════╝\n\n"

        "⚙️ Select management option:",

        parse_mode=ParseMode.HTML,

        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
#                     /getnumber_set
# ============================================================

async def getnumber_set(update, context):

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text

    parts = text.split(maxsplit=1)

    if len(parts) < 2:

        await update.message.reply_text(
            "Example:\n\n"
            "/getnumber_set Instagram Facebook WhatsApp"
        )

        return

    names = re.split(
        r"[\s,]+",
        parts[1]
    )

    added = []

    for name in names:

        key = ALIASES.get(
            name.lower().strip()
        )

        if not key:
            continue

        db.execute(
            """
            UPDATE services
            SET enabled=1
            WHERE service=?
            """,
            (key,)
        )

        added.append(
            SERVICES[key]["name"]
        )

    db.commit()

    if added:

        await update.message.reply_text(
            "✅ <b>Services Enabled</b>\n\n"
            + "\n".join(
                f"🟢 {x}" for x in added
            ),
            parse_mode=ParseMode.HTML
        )

    else:

        await update.message.reply_text(
            "❌ No valid service found."
        )


# ============================================================
#                /getnumber_remove_SERVICE
# ============================================================

async def getnumber_remove(update, context):

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text

    match = re.match(
        r"^/getnumber_remove_(.+)$",
        text,
        re.I
    )

    if not match:
        return

    name = match.group(1).strip()

    key = ALIASES.get(
        name.lower()
    )

    if not key:

        await update.message.reply_text(
            "❌ Service not found."
        )

        return

    db.execute(
        """
        UPDATE services
        SET enabled=0
        WHERE service=?
        """,
        (key,)
    )

    db.commit()

    await update.message.reply_text(

        f"✅ <b>{SERVICES[key]['name']}</b> "
        f"removed from Get Number.",

        parse_mode=ParseMode.HTML
    )


# ============================================================
#                   ADD COUNTRY
# ============================================================

async def add_country(update, context):

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text

    match = re.match(
        r"^/getnumber_([A-Za-z0-9]+)_country\s+(.+)$",
        text,
        re.I | re.S
    )

    if not match:

        await update.message.reply_text(

            "Example:\n\n"
            "/getnumber_instagram_country "
            "🇵🇸 Sudan - 0.8Tk/OTP"
        )

        return

    service_name_input = match.group(1)

    country = match.group(2).strip()

    service = ALIASES.get(
        service_name_input.lower()
    )

    if not service:

        await update.message.reply_text(
            "❌ Service not found."
        )

        return

    db.execute(
        """
        INSERT INTO countries
        (service, country)
        VALUES (?, ?)
        """,

        (
            service,
            country
        )
    )

    db.commit()

    await update.message.reply_text(

        "✅ <b>Country Added</b>\n\n"

        f"📱 Service: "
        f"{SERVICES[service]['name']}\n"

        f"🌍 Country: "
        f"{country}",

        parse_mode=ParseMode.HTML
    )


# ============================================================
#                     REMOVE COUNTRY
# ============================================================

async def remove_country(update, context):

    if not is_admin(update.effective_user.id):
        return

    text = update.message.text

    match = re.match(
        r"^/getnumber_country_(.+)_remov$",
        text,
        re.I | re.S
    )

    if not match:
        return

    country = match.group(1).strip()

    cursor = db.execute(
        """
        DELETE FROM countries
        WHERE country=?
        """,
        (country,)
    )

    db.commit()

    if cursor.rowcount:

        await update.message.reply_text(
            "✅ Country removed successfully."
        )

    else:

        await update.message.reply_text(
            "⚠️ Country not found."
        )


# ============================================================
#                  SET USER STATS
# ============================================================

async def set_userstats(update, context):

    if not is_admin(update.effective_user.id):
        return

    lines = update.message.text.splitlines()

    first_line = lines[0]

    match = re.match(
        r"^/set_userstasts_(\d+)$",
        first_line.strip(),
        re.I
    )

    if not match:

        await update.message.reply_text(

            "Example:\n\n"

            "/set_userstasts_123456789\n"
            "Subscription :- 🟢 Active\n"
            "Subscription Price :- 5$\n"
            "Duration :- 30DAY\n"
            "Total Earning :- 8$\n"
            "My Balance :- 8$"
        )

        return

    user_id = int(
        match.group(1)
    )

    data = {}

    for line in lines[1:]:

        if ":" not in line:
            continue

        key, value = line.split(
            ":",
            1
        )

        key = key.strip().lower()

        value = value.strip()

        if key == "subscription":

            data["subscription"] = (
                1
                if "active" in value.lower()
                else 0
            )

        elif key == "subscription price":

            data["subscription_price"] = value

        elif key == "duration":

            data["duration"] = value

        elif key == "total earning":

            data["total_earning"] = value

        elif key == "my balance":

            number = re.sub(
                r"[^0-9.\-]",
                "",
                value
            )

            data["balance"] = (
                float(number)
                if number
                else 0
            )

    # User না থাকলে create
    if not get_user(user_id):

        db.execute(
            """
            INSERT INTO users
            (user_id, created_at)
            VALUES (?, ?)
            """,
            (
                user_id,
                datetime.now().isoformat()
            )
        )

    if data:

        fields = []

        values = []

        for key, value in data.items():

            fields.append(
                f"{key}=?"
            )

            values.append(value)

        values.append(user_id)

        db.execute(
            f"""
            UPDATE users
            SET {', '.join(fields)}
            WHERE user_id=?
            """,
            values
        )

        db.commit()

    await update.message.reply_text(

        f"✅ <b>User Stats Updated</b>\n\n"
        f"User ID: <code>{user_id}</code>",

        parse_mode=ParseMode.HTML
    )


# ============================================================
#                         BAN
# ============================================================

async def ban(update, context):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "/ban USER_ID"
        )

        return

    if not context.args[0].isdigit():

        await update.message.reply_text(
            "❌ Invalid User ID."
        )

        return

    user_id = int(
        context.args[0]
    )

    db.execute(
        """
        UPDATE users
        SET banned=1
        WHERE user_id=?
        """,
        (user_id,)
    )

    db.commit()

    await update.message.reply_text(
        f"🚫 User <code>{user_id}</code> banned.",
        parse_mode=ParseMode.HTML
    )


# ============================================================
#                         UNBAN
# ============================================================

async def unban(update, context):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "/unban USER_ID"
        )

        return

    user_id = int(
        context.args[0]
    )

    db.execute(
        """
        UPDATE users
        SET banned=0
        WHERE user_id=?
        """,
        (user_id,)
    )

    db.commit()

    await update.message.reply_text(
        f"✅ User <code>{user_id}</code> unbanned.",
        parse_mode=ParseMode.HTML
    )


# ============================================================
#                       BROADCAST
# ============================================================

async def broadcast(update, context):

    if not is_admin(update.effective_user.id):
        return

    if not context.args:

        await update.message.reply_text(
            "/broadcast Your message"
        )

        return

    message = update.message.text.split(
        maxsplit=1
    )[1]

    users = db.execute(
        """
        SELECT user_id
        FROM users
        WHERE banned=0
        """
    ).fetchall()

    success = 0
    failed = 0

    for user in users:

        try:

            await context.bot.send_message(
                user["user_id"],
                message
            )

            success += 1

            await asyncio.sleep(
                0.05
            )

        except Exception:

            failed += 1

    await update.message.reply_text(

        "📢 <b>Broadcast Finished</b>\n\n"

        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}",

        parse_mode=ParseMode.HTML
    )


# ============================================================
#                     SUPPORT SETUP
# ============================================================

async def support_setup(update, context):

    if not is_admin(update.effective_user.id):
        return

    context.user_data["support_setup"] = True
    context.user_data["support_values"] = []
    context.user_data["support_count"] = None

    await update.message.reply_text(

        "🆘 <b>SUPPORT SETUP</b>\n\n"

        "আপনি কয়টি Support ID add করতে চান?\n\n"

        "Example: <code>3</code>\n\n"

        "তারপর একে একে username / ID / "
        "profile link পাঠাবেন।",

        parse_mode=ParseMode.HTML
    )


async def support_setup_message(update, context):

    if not is_admin(update.effective_user.id):
        return False

    if not context.user_data.get(
        "support_setup"
    ):
        return False

    text = (
        update.message.text or ""
    ).strip()

    # প্রথমে কয়টি Support
    if context.user_data["support_count"] is None:

        if not text.isdigit():

            await update.message.reply_text(
                "❌ শুধু সংখ্যা দিন। Example: 3"
            )

            return True

        count = int(text)

        if count < 1 or count > 10:

            await update.message.reply_text(
                "❌ 1 থেকে 10-এর মধ্যে দিন।"
            )

            return True

        context.user_data[
            "support_count"
        ] = count

        await update.message.reply_text(

            f"✅ {count}টি Support ID লাগবে।\n\n"
            "এখন প্রথম Support ID পাঠান।"

        )

        return True

    values = context.user_data[
        "support_values"
    ]

    values.append(text)

    count = context.user_data[
        "support_count"
    ]

    current = len(values)

    if current < count:

        await update.message.reply_text(

            f"✅ Saved {current}/{count}\n"
            "Next Support ID পাঠান।"

        )

        return True

    # Database update
    db.execute(
        "DELETE FROM supports"
    )

    for value in values:

        db.execute(
            """
            INSERT INTO supports(value)
            VALUES(?)
            """,
            (value,)
        )

    db.commit()

    context.user_data.clear()

    await update.message.reply_text(

        f"✅ <b>Support Setup Complete</b>\n\n"
        f"Total Support: {count}",

        parse_mode=ParseMode.HTML
    )

    return True


# ============================================================
#                     INCOMING NUMBER
# ============================================================

def parse_number(text):

    parts = text.split()

    if len(parts) < 2:
        return None

    service = None
    service_index = -1

    for i, part in enumerate(parts[:7]):

        key = ALIASES.get(
            part.lower().strip(":-")
        )

        if key:

            service = key
            service_index = i

            break

    if not service:
        return None

    number = None

    for part in parts[
        service_index + 1:
    ]:

        clean = re.sub(
            r"[^\d+]",
            "",
            part
        )

        digits = re.sub(
            r"\D",
            "",
            clean
        )

        if len(digits) >= 8:

            number = clean

            break

    if not number:
        return None

    country = " ".join(
        parts[:service_index]
    )

    return country, service, number


async def incoming_number(
    update,
    context
):

    user = update.effective_user

    ensure_user(user)

    row = get_user(user.id)

    if row["banned"]:
        return

    text = update.message.text or ""

    parsed = parse_number(text)

    if not parsed:
        return

    country, service, number = parsed

    # Random 6 digit code
    code = str(
        random.randint(
            100000,
            999999
        )
    )

    label = SERVICES[
        service
    ]["name"]

    emoji = service_emoji(
        service
    )

    await update.message.reply_text(

        f"{country} "
        f"{emoji} "
        f"<b>{label}</b> "
        f"<code>{number}</code>\n\n"

        f"🔐 <b>CODE:</b> "
        f"<code>{code}</code>",

        parse_mode=ParseMode.HTML
    )


# ============================================================
#                       CALLBACKS
# ============================================================

async def callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    ensure_user(user)

    row = get_user(user.id)

    if row["banned"]:

        await query.edit_message_text(
            "🚫 <b>You are banned.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    data = query.data

    # ---------------- HOME ----------------

    if data == "home":

        await query.edit_message_text(

            "╔══════════════════════╗\n"
            "       <b>SECRET NUMBER BOT</b>\n"
            "╚══════════════════════╝\n\n"

            "🌟 Select an option:",

            parse_mode=ParseMode.HTML,

            reply_markup=main_menu(
                user.id
            )
        )

    # ---------------- GET NUMBER ----------------

    elif data == "get_number":

        await get_number_page(
            query
        )

    # ---------------- SERVICE ----------------

    elif data.startswith(
        "service:"
    ):

        service = data.split(
            ":",
            1
        )[1]

        if service in SERVICES:

            await service_page(
                query,
                service
            )

    # ---------------- COUNTRY ----------------

    elif data.startswith(
        "country:"
    ):

        country_id = int(
            data.split(
                ":",
                1
            )[1]
        )

        country = db.execute(

            """
            SELECT *
            FROM countries
            WHERE id=?
            """,

            (country_id,)

        ).fetchone()

        if not country:

            await query.answer(
                "Country not found.",
                show_alert=True
            )

            return

        # Subscription check
        if not row["subscription"]:

            await query.answer(
                "Your subscription not active ❌",
                show_alert=True
            )

            await query.edit_message_text(

                "❌ <b>Your subscription not active</b>\n\n"

                "Please contact support to activate "
                "your subscription.",

                parse_mode=ParseMode.HTML,

                reply_markup=InlineKeyboardMarkup([

                    [
                        InlineKeyboardButton(
                            "🆘 Support",
                            callback_data="support"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            "🔙 Back",
                            callback_data=
                            f"service:{country['service']}"
                        )
                    ]
                ])
            )

            return

        # Active subscription
        await query.edit_message_text(

            "✅ <b>Subscription Active</b>\n\n"

            f"🌍 {country['country']}\n\n"

            "Number allocation is available.",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data=
                        f"service:{country['service']}"
                    )
                ]
            ])
        )

    # ---------------- STATS ----------------

    elif data == "stats":

        await stats_page(
            query,
            user.id
        )

    # ---------------- WITHDRAW ----------------

    elif data == "withdraw":

        await withdraw_page(
            query
        )

    elif data.startswith(
        "withdraw:"
    ):

        await query.answer(
            f"Minimum Withdraw {MIN_WITHDRAW} Tk",
            show_alert=True
        )

    # ---------------- SUPPORT ----------------

    elif data == "support":

        await support_page(
            query
        )

    elif data == "support_info":

        await query.answer(
            "Please use the support contact.",
            show_alert=True
        )

    # ---------------- ADMIN ----------------

    elif data == "admin":

        await admin_page(
            query
        )

    # ---------------- ADMIN STATS ----------------

    elif data == "admin_stats":

        if not is_admin(user.id):
            return

        total = db.execute(
            "SELECT COUNT(*) c FROM users"
        ).fetchone()["c"]

        banned = db.execute(
            """
            SELECT COUNT(*) c
            FROM users
            WHERE banned=1
            """
        ).fetchone()["c"]

        active = db.execute(
            """
            SELECT COUNT(*) c
            FROM users
            WHERE subscription=1
            """
        ).fetchone()["c"]

        await query.edit_message_text(

            "📊 <b>BOT STATISTICS</b>\n\n"

            f"👥 Total Users: <b>{total}</b>\n\n"
            f"🟢 Active Subscription: <b>{active}</b>\n\n"
            f"🚫 Banned Users: <b>{banned}</b>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN SERVICES ----------------

    elif data == "admin_services":

        if not is_admin(user.id):
            return

        active = set(
            active_services()
        )

        text = (
            "📱 <b>GET NUMBER SERVICES</b>\n\n"
        )

        for key in SERVICES:

            status = (
                "🟢 ON"
                if key in active
                else "🔴 OFF"
            )

            text += (
                f"{status} "
                f"{SERVICES[key]['name']}\n"
            )

        text += (

            "\n<b>Commands:</b>\n\n"

            "<code>/getnumber_set "
            "Instagram Facebook WhatsApp</code>\n\n"

            "<code>/getnumber_remove_Facebook</code>"
        )

        await query.edit_message_text(

            text,

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN COUNTRIES ----------------

    elif data == "admin_countries":

        if not is_admin(user.id):
            return

        await query.edit_message_text(

            "🌍 <b>COUNTRY MANAGER</b>\n\n"

            "<b>Add Country:</b>\n"

            "<code>/getnumber_instagram_country "
            "🇵🇸 Sudan - 0.8Tk/OTP</code>\n\n"

            "<b>Remove Country:</b>\n"

            "<code>/getnumber_country_"
            "🇵🇸 Sudan - 0.8Tk/OTP_remov</code>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN USER STATS ----------------

    elif data == "admin_userstats":

        if not is_admin(user.id):
            return

        await query.edit_message_text(

            "👤 <b>USER STATS MANAGER</b>\n\n"

            "Example:\n\n"

            "<code>/set_userstasts_123456789\n"
            "Subscription :- 🟢 Active\n"
            "Subscription Price :- 5$\n"
            "Duration :- 30DAY\n"
            "Total Earning :- 8$\n"
            "My Balance :- 8$</code>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN SUPPORT ----------------

    elif data == "admin_support":

        if not is_admin(user.id):
            return

        supports = db.execute(
            "SELECT value FROM supports ORDER BY id"
        ).fetchall()

        current = "\n".join(

            f"{i+1}. {x['value']}"

            for i, x in enumerate(supports)
        )

        if not current:
            current = "No support configured."

        await query.edit_message_text(

            "🆘 <b>SUPPORT MANAGER</b>\n\n"

            f"{current}\n\n"

            "To configure:\n"
            "<code>/support_setup</code>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN BAN ----------------

    elif data == "admin_ban":

        if not is_admin(user.id):
            return

        await query.edit_message_text(

            "🚫 <b>BAN / UNBAN</b>\n\n"

            "<code>/ban USER_ID</code>\n\n"

            "<code>/unban USER_ID</code>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )

    # ---------------- ADMIN BROADCAST ----------------

    elif data == "admin_broadcast":

        if not is_admin(user.id):
            return

        await query.edit_message_text(

            "📢 <b>BROADCAST</b>\n\n"

            "Use:\n\n"

            "<code>/broadcast Your message</code>",

            parse_mode=ParseMode.HTML,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 Admin Panel",
                        callback_data="admin"
                    )
                ]
            ])
        )


# ============================================================
#                         MAIN
# ============================================================

async def text_router(
    update,
    context
):

    # Support setup চলছে কিনা
    if await support_setup_message(
        update,
        context
    ):

        return

    # Number message
    await incoming_number(
        update,
        context
    )


def main():

    if (
        not BOT_TOKEN
        or BOT_TOKEN ==
        "PASTE_YOUR_BOT_TOKEN_HERE"
    ):

        print(
            "❌ BOT_TOKEN বসানো হয়নি!"
        )

        return

    if not ADMIN_IDS:

        print(
            "❌ ADMIN_IDS বসানো হয়নি!"
        )

        return

    print(
        "================================"
    )

    print(
        "   SECRET NUMBER BOT STARTING"
    )

    print(
        "================================"
    )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "getnumber_set",
            getnumber_set
        )
    )

    app.add_handler(
        CommandHandler(
            "ban",
            ban
        )
    )

    app.add_handler(
        CommandHandler(
            "unban",
            unban
        )
    )

    app.add_handler(
        CommandHandler(
            "broadcast",
            broadcast
        )
    )

    app.add_handler(
        CommandHandler(
            "support_setup",
            support_setup
        )
    )

    # Special commands
    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^/getnumber_remove_.+"
            ),
            getnumber_remove
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^/getnumber_[A-Za-z0-9]+_country\s+.+"
            ),
            add_country
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^/getnumber_country_.+_remov$"
            ),
            remove_country
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^/set_userstasts_\d+"
            ),
            set_userstats
        )
    )

    # Buttons
    app.add_handler(
        CallbackQueryHandler(
            callback
        )
    )

    # Normal text
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_router
        )
    )

    print(
        "✅ BOT IS RUNNING..."
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
#                         RUN
# ============================================================

if __name__ == "__main__":

    main()
