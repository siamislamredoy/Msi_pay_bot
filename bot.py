import telebot
import sqlite3
from datetime import datetime

API_KEY = '7576082738:AAHHUX4XhY0FwAwhu-lLbAhhfQcI8V0gEn4'
ADMIN_IDS = [7901308168]  # এখানে অ্যাডমিন আইডি বসান
WITHDRAW_CHANNEL_ID = -1002439365996  # উইথড্র চ্যানেল আইডি
RECHARGE_CHANNEL_ID = -1002439365996  # রিচার্জ চ্যানেল আইডি

bot = telebot.TeleBot(API_KEY)

# ডেটাবেস তৈরি
def init_db():
    conn = sqlite3.connect("balances.db")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        amount INTEGER,
        type TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ব্যালেন্স আপডেট
def update_balance(user_id, amount):
    conn = sqlite3.connect("balances.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ব্যালেন্স দেখানো
def get_balance(user_id):
    conn = sqlite3.connect("balances.db")
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

# লেনদেন রেকর্ড
def record_transaction(sender, receiver, amount, tx_type):
    conn = sqlite3.connect("balances.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (sender_id, receiver_id, amount, type, timestamp) VALUES (?, ?, ?, ?, ?)",
        (sender, receiver, amount, tx_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# /balance
@bot.message_handler(commands=['balance'])
def balance(message):
    bal = get_balance(message.from_user.id)
    bot.reply_to(message, f"💰 আপনার বর্তমান ব্যালেন্স: {bal} টাকা")

# /ing user_id amount
@bot.message_handler(commands=['ing'])
def admin_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        update_balance(user_id, amount)
        record_transaction(message.from_user.id, user_id, amount, "admin_add")
        bot.reply_to(message, f"✅ {user_id} ইউজারের অ্যাকাউন্টে {amount} টাকা অ্যাড করা হয়েছে।")
        bot.send_message(user_id, f"📥 আপনার অ্যাকাউন্টে {amount} টাকা অ্যাড হয়েছে।")
    except:
        bot.reply_to(message, "❌ কমান্ড ফরম্যাট ভুল।\nপ্রয়োগ: /ing user_id amount")

# /dig user_id amount
@bot.message_handler(commands=['dig'])
def admin_deduct_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        user_id = int(parts[1])
        amount = int(parts[2])
        if get_balance(user_id) < amount:
            bot.reply_to(message, "❌ ইউজারের পর্যাপ্ত ব্যালেন্স নেই।")
            return
        update_balance(user_id, -amount)
        record_transaction(user_id, message.from_user.id, amount, "admin_deduct")
        bot.reply_to(message, f"✅ {user_id} ইউজারের অ্যাকাউন্ট থেকে {amount} টাকা কাটা হয়েছে।")
        bot.send_message(user_id, f"📤 আপনার অ্যাকাউন্ট থেকে {amount} টাকা কাটা হয়েছে।")
    except:
        bot.reply_to(message, "❌ কমান্ড ফরম্যাট ভুল।\nপ্রয়োগ: /dig user_id amount")

# /send user_id amount
@bot.message_handler(commands=['send'])
def send_balance(message):
    try:
        parts = message.text.split()
        receiver = int(parts[1])
        amount = int(parts[2])
        sender = message.from_user.id

        if get_balance(sender) < amount:
            bot.reply_to(message, "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই।")
            return

        update_balance(sender, -amount)
        update_balance(receiver, amount)
        record_transaction(sender, receiver, amount, "send")

        bot.reply_to(message, f"✅ আপনি {receiver} ইউজারকে {amount} টাকা পাঠিয়েছেন।")
        bot.send_message(receiver, f"📥 আপনি {sender} ইউজার থেকে {amount} টাকা পেয়েছেন।")
    except:
        bot.reply_to(message, "❌ কমান্ড ফরম্যাট ভুল।\nপ্রয়োগ: /send user_id amount")

# /withdraw 01xxxxxxxxx amount
@bot.message_handler(commands=['withdraw'])
def withdraw(message):
    try:
        parts = message.text.split()
        number = parts[1]
        amount = int(parts[2])
        user_id = message.from_user.id
        total = int(amount * 1.1)

        if get_balance(user_id) < total:
            bot.reply_to(message, "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই।")
            return

        update_balance(user_id, -total)
        record_transaction(user_id, 0, amount, "withdraw")

        forward_msg = f"📤 উইথড্র রিকুয়েস্ট\n👤 ইউজার: {user_id}\n📞 নাম্বার: {number}\n💰 এমাউন্ট: {amount} টাকা (১০% ফি সহ কাটা হয়েছে {total})"
        bot.send_message(WITHDRAW_CHANNEL_ID, forward_msg)
        bot.reply_to(message, f"✅ {amount} টাকা উইথড্র রিকুয়েস্ট গ্রহণ করা হয়েছে।")
    except:
        bot.reply_to(message, "❌ কমান্ড ফরম্যাট ভুল।\nপ্রয়োগ: /withdraw 01xxxxxxxxx amount")

# /recharge 01xxxxxxxxx amount
@bot.message_handler(commands=['recharge'])
def recharge(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            raise ValueError("Invalid format")
        
        number = parts[1]
        if not number.isdigit() or not number.startswith("01") or len(number) != 11:
            raise ValueError("Invalid number")

        amount = int(parts[2])
        if amount <= 0:
            raise ValueError("Amount must be positive")

        user_id = message.from_user.id
        total = amount + 5

        if get_balance(user_id) < total:
            bot.reply_to(message, "❌ পর্যাপ্ত ব্যালেন্স নেই।")
            return

        update_balance(user_id, -total)
        record_transaction(user_id, 0, amount, "recharge")

        forward_msg = f"🔋 রিচার্জ রিকুয়েস্ট\n👤 ইউজার: {user_id}\n📞 নাম্বার: {number}\n💰 এমাউন্ট: {amount} টাকা (+৫ টাকা ফি)"
        bot.send_message(RECHARGE_CHANNEL_ID, forward_msg)
        bot.reply_to(message, f"✅ {amount} টাকা রিচার্জ রিকুয়েস্ট গ্রহণ করা হয়েছে।")

    except ValueError as e:
        bot.reply_to(message, "❌ কিছু ভুল হয়েছে।\nসঠিকভাবে লিখুন: /recharge 01xxxxxxxxx amount")
    except Exception as e:
        bot.reply_to(message, f"⚠️ একটি ত্রুটি ঘটেছে: {str(e)}")

# /history
@bot.message_handler(commands=['history'])
def history(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("balances.db")
    cur = conn.cursor()
    cur.execute("""SELECT sender_id, receiver_id, amount, type, timestamp
                   FROM transactions
                   WHERE sender_id = ? OR receiver_id = ?
                   ORDER BY timestamp DESC
                   LIMIT 20""", (user_id, user_id))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.reply_to(message, "📭 কোনো লেনদেন পাওয়া যায়নি।")
        return

    msg = "📜 আপনার সর্বশেষ ২০টি লেনদেন:\n\n"
    for s, r, a, t, ts in rows:
        if t == "send":
            if s == user_id:
                msg += f"🔴 আপনি {r} কে পাঠিয়েছেন — {a} টাকা\n🕓 {ts}\n\n"
            else:
                msg += f"🟢 আপনি {s} থেকে পেয়েছেন — {a} টাকা\n🕓 {ts}\n\n"
        elif t == "withdraw":
            msg += f"📤 উইথড্র করেছেন — {a} টাকা\n🕓 {ts}\n\n"
        elif t == "recharge":
            msg += f"🔋 রিচার্জ করেছেন — {a} টাকা\n🕓 {ts}\n\n"
        elif t == "admin_add":
            msg += f"➕ অ্যাডমিন {s} আপনার অ্যাকাউন্টে {a} টাকা অ্যাড করেছেন\n🕓 {ts}\n\n"
        elif t == "admin_deduct":
            msg += f"➖ অ্যাডমিন আপনার অ্যাকাউন্ট থেকে {a} টাকা কেটে নিয়েছেন\n🕓 {ts}\n\n"

    bot.reply_to(message, msg)
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """🛠️ *বট কমান্ড তালিকা*:

📌 /balance - আপনার বর্তমান ব্যালেন্স দেখুন  
📌 /send `user_id amount` - অন্য ইউজারকে টাকা পাঠান  
📌 /withdraw `01xxxxxxxxx amount` - উইথড্র রিকুয়েস্ট (১০% ফি সহ কাটা হবে)  
📌 /recharge `01xxxxxxxxx amount` - মোবাইল রিচার্জ রিকুয়েস্ট (৫ টাকা ফি কাটা হবে)  
📌 /history - সর্বশেষ ২০টি লেনদেনের বিস্তারিত দেখুন  
📌 /accinfo - আপনার ইনফো আসবে

👮‍♂️ *শুধু অ্যাডমিনদের জন্য:*  
🔧 /ing `user_id amount` - ইউজারের অ্যাকাউন্টে টাকা অ্যাড করুন  
🔧 /dig `user_id amount` - ইউজারের অ্যাকাউন্ট থেকে টাকা কেটে নিন
"""
    bot.reply_to(message, help_text, parse_mode="Markdown")
@bot.message_handler(commands=['accinfo'])
def acc_info(message):
    user = message.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "—"
    user_id = user.id

    msg = f"""👤 *Account Info*

📛 নাম: *{full_name}*  
🔖 ইউজারনেম: {username}  
🆔 ইউজার আইডি: `{user_id}`
"""
    bot.reply_to(message, msg, parse_mode="Markdown")
# বট চালু
print("✅ Bot is running...")
bot.polling(non_stop=True)