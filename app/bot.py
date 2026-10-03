import asyncio
from datetime import date

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from app.config import *
from app.db import *


def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🚀 Open Clipcaps",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ],
        [
            InlineKeyboardButton(
                "🎯 Daily Tasks",
                callback_data="tasks"
            )
        ],
        [
            InlineKeyboardButton(
                "🎁 Daily Bonus",
                callback_data="daily"
            ),
            InlineKeyboardButton(
                "💰 Balance",
                callback_data="balance"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Convert",
                callback_data="convert"
            ),
            InlineKeyboardButton(
                "💸 Withdraw",
                callback_data="withdraw"
            ),
        ],
    ])


def task_menu():
    today = str(date.today())

    buttons = []

    for task_id, title, url in TASKS:
        buttons.append([
            InlineKeyboardButton(
                title,
                callback_data=f"open_{task_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Back",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def withdraw_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "bKash",
                callback_data="wd_bkash"
            ),
            InlineKeyboardButton(
                "Nagad",
                callback_data="wd_nagad"
            ),
        ],
        [
            InlineKeyboardButton(
                "Rocket",
                callback_data="wd_rocket"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back"
            )
        ],
    ])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ref = None

    if ctx.args:
        try:
            ref = int(ctx.args[0])
        except:
            pass

    upsert(
        u.id,
        u.username or "",
        u.first_name or "",
        ref,
        REFERRAL_BONUS
    )

    r = user(u.id)

    await update.message.reply_text(
        f"✨ <b>Welcome to Clipcaps</b>, {u.first_name}!\n\n"
        f"💰 Balance: <b>{r['coins']}</b> points\n"
        f"🎁 Daily bonus: <b>+{DAILY_BONUS}</b> points\n\n"
        "🎯 Complete daily tasks to earn more points.",
        parse_mode="HTML",
        reply_markup=menu()
    )


async def show_tasks(q):
    await q.message.reply_text(
        "🎯 <b>Daily Tasks</b>\n\n"
        "Complete each task once per day.\n"
        f"💰 Reward: <b>+{TASK_REWARD} points</b> each\n"
        f"⏳ Wait: <b>{TASK_WAIT_SECONDS} seconds</b>",
        parse_mode="HTML",
        reply_markup=task_menu()
    )


async def start_task(q, ctx, task_id):
    today = str(date.today())
    uid = q.from_user.id

    task = next(
        (x for x in TASKS if x[0] == task_id),
        None
    )

    if not task:
        return

    if task_claimed(uid, task_id, today):
        await q.message.reply_text(
            "✅ You already completed this task today."
        )
        return

    _, title, url = task

    # Store timer start
    ctx.user_data[f"task_start_{task_id}"] = asyncio.get_running_loop().time()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔗 Open Task",
                url=url
            )
        ],
        [
            InlineKeyboardButton(
                f"⏳ Wait {TASK_WAIT_SECONDS}s",
                callback_data=f"wait_{task_id}"
            )
        ]
    ])

    await q.message.reply_text(
        f"{title}\n\n"
        f"1️⃣ Open the link\n"
        f"2️⃣ Stay there for {TASK_WAIT_SECONDS} seconds\n"
        f"3️⃣ Come back and press the timer button\n\n"
        "⚠️ You can claim this task only once today.",
        reply_markup=keyboard
    )


async def check_task(q, ctx, task_id):
    today = str(date.today())
    uid = q.from_user.id

    if task_claimed(uid, task_id, today):
        await q.message.reply_text(
            "✅ You already completed this task today."
        )
        return

    key = f"task_start_{task_id}"
    started = ctx.user_data.get(key)

    if not started:
        await q.message.reply_text(
            "❌ Please open the task first."
        )
        return

    elapsed = asyncio.get_running_loop().time() - started

    if elapsed < TASK_WAIT_SECONDS:
        remaining = int(
            TASK_WAIT_SECONDS - elapsed
        ) + 1

        await q.message.reply_text(
            f"⏳ Please wait {remaining} more seconds."
        )
        return

    ok = task_claim(
        uid,
        task_id,
        today,
        TASK_REWARD
    )

    ctx.user_data.pop(key, None)

    if ok:
        r = user(uid)

        await q.message.reply_text(
            f"🎉 Task completed!\n\n"
            f"💰 +{TASK_REWARD} points added.\n"
            f"💰 Current balance: {r['coins']} points"
        )
    else:
        await q.message.reply_text(
            "❌ This task has already been claimed today."
        )


async def ask_withdraw_method(q, ctx, method):
    ctx.user_data["withdraw_method"] = method

    await q.message.reply_text(
        f"💸 <b>{method.title()} Withdrawal</b>\n\n"
        f"Minimum: <b>{MIN_WITHDRAW_COINS} points</b>\n"
        f"Rate: <b>1 point = ৳{COIN_TO_BDT:.2f}</b>\n\n"
        "Send your mobile/account number.",
        parse_mode="HTML"
    )

    ctx.user_data["awaiting_withdraw_number"] = True


async def text_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("awaiting_withdraw_number"):
        return

    number = update.message.text.strip()
    method = ctx.user_data.get("withdraw_method")

    if not number.isdigit():
        await update.message.reply_text(
            "❌ Please send a valid number."
        )
        return

    uid = update.effective_user.id
    r = user(uid)

    if not r or r["coins"] < MIN_WITHDRAW_COINS:
        await update.message.reply_text(
            f"❌ Minimum withdrawal is "
            f"{MIN_WITHDRAW_COINS} points."
        )
        ctx.user_data.clear()
        return

    ctx.user_data["withdraw_number"] = number
    ctx.user_data["awaiting_withdraw_number"] = False

    await update.message.reply_text(
        "💰 How many points do you want to withdraw?\n\n"
        f"Available: {r['coins']} points\n"
        f"Minimum: {MIN_WITHDRAW_COINS} points\n"
        f"Rate: 1 point = ৳{COIN_TO_BDT:.2f}\n\n"
        "Example: 1000"
    )

    ctx.user_data["awaiting_withdraw_amount"] = True


async def withdraw_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("awaiting_withdraw_amount"):
        return

    try:
        coins = int(update.message.text.strip())
    except:
        await update.message.reply_text(
            "❌ Please enter a valid points amount."
        )
        return

    uid = update.effective_user.id
    r = user(uid)

    if coins < MIN_WITHDRAW_COINS:
        await update.message.reply_text(
            f"❌ Minimum is {MIN_WITHDRAW_COINS} points."
        )
        return

    if not r or coins > r["coins"]:
        await update.message.reply_text(
            "❌ You don't have enough points."
        )
        return

    method = ctx.user_data["withdraw_method"]
    number = ctx.user_data["withdraw_number"]
    amount = coins * COIN_TO_BDT

    ok = withdraw(
        uid,
        method,
        number,
        coins,
        amount
    )

    if not ok:
        await update.message.reply_text(
            "❌ Withdrawal failed. Please try again."
        )
        return

    await update.message.reply_text(
        f"✅ <b>Withdrawal Request Submitted</b>\n\n"
        f"🏦 Method: {method.title()}\n"
        f"📱 Number: {number}\n"
        f"💰 Points: {coins}\n"
        f"💵 Amount: ৳{amount:.2f}\n"
        f"⏳ Status: Pending",
        parse_mode="HTML"
    )

    # Notify admin
    if ADMIN_ID:
        await ctx.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>New Withdrawal</b>\n\n"
            f"👤 User: {uid}\n"
            f"🏦 Method: {method.title()}\n"
            f"📱 Number: {number}\n"
            f"💰 Points: {coins}\n"
            f"💵 Amount: ৳{amount:.2f}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Approve",
                        callback_data=f"approve_{get_last_withdrawal(uid)}"
                    ),
                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=f"reject_{get_last_withdrawal(uid)}"
                    )
                ]
            ])
        )

    ctx.user_data.clear()


def get_last_withdrawal(uid):
    rows = withdrawals("pending")

    for row in rows:
        if row["user_id"] == uid:
            return row["id"]

    return 0


async def cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    data = q.data

    if data == "back":
        await q.message.reply_text(
            "🏠 Main Menu",
            reply_markup=menu()
        )
        return

    if data == "balance":
        r = user(uid)

        amount = r["coins"] * COIN_TO_BDT

        await q.message.reply_text(
            f"💰 <b>Balance</b>\n\n"
            f"🪙 Points: <b>{r['coins']}</b>\n"
            f"💵 Value: <b>৳{amount:.2f}</b>",
            parse_mode="HTML"
        )

    elif data == "convert":
        r = user(uid)
        amount = r["coins"] * COIN_TO_BDT

        await q.message.reply_text(
            f"🔄 <b>Points → Taka</b>\n\n"
            f"🪙 Your points: <b>{r['coins']}</b>\n"
            f"💵 Conversion value: <b>৳{amount:.2f}</b>\n\n"
            f"📌 Rate:\n"
            f"1 point = ৳{COIN_TO_BDT:.2f}\n\n"
            "You don't need to manually convert your points. "
            "Withdrawal automatically uses this conversion rate.",
            parse_mode="HTML"
        )

    elif data == "tasks":
        await show_tasks(q)

    elif data.startswith("open_"):
        task_id = data.replace("open_", "")
        await start_task(q, ctx, task_id)

    elif data.startswith("wait_"):
        task_id = data.replace("wait_", "")
        await check_task(q, ctx, task_id)

    elif data == "daily":
        ok = daily(
            uid,
            str(date.today()),
            DAILY_BONUS
        )

        await q.message.reply_text(
            f"🎁 +{DAILY_BONUS} points added!"
            if ok
            else "⏳ Daily bonus already claimed today."
        )

    elif data == "withdraw":
        r = user(uid)

        if r["coins"] < MIN_WITHDRAW_COINS:
            await q.message.reply_text(
                f"❌ Minimum withdrawal is "
                f"{MIN_WITHDRAW_COINS} points.\n\n"
                f"Your balance: {r['coins']} points"
            )
            return

        await q.message.reply_text(
            "💸 Select withdrawal method:",
            reply_markup=withdraw_menu()
        )

    elif data.startswith("wd_"):
        method = data.replace("wd_", "")
        await ask_withdraw_method(
            q,
            ctx,
            method
        )

    elif data.startswith("approve_"):
        if uid != ADMIN_ID:
            return

        wid = int(data.replace("approve_", ""))

        ok = set_status(
            wid,
            "paid"
        )

        if ok:
            w = get_withdrawal(wid)

            await q.message.reply_text(
                f"✅ Withdrawal #{wid} marked as PAID."
            )

            if w:
                await ctx.bot.send_message(
                    w["user_id"],
                    f"✅ <b>Withdrawal Paid</b>\n\n"
                    f"💵 Amount: ৳{w['amount_bdt']:.2f}\n"
                    f"🏦 Method: {w['method'].title()}\n"
                    f"📱 Number: {w['number']}",
                    parse_mode="HTML"
                )

        else:
            await q.message.reply_text(
                "❌ Already processed or not found."
            )

    elif data.startswith("reject_"):
        if uid != ADMIN_ID:
            return

        wid = int(data.replace("reject_", ""))

        w = get_withdrawal(wid)

        ok = set_status(
            wid,
            "rejected"
        )

        if ok:
            await q.message.reply_text(
                f"❌ Withdrawal #{wid} rejected.\n"
                f"💰 Points refunded."
            )

            if w:
                await ctx.bot.send_message(
                    w["user_id"],
                    f"❌ <b>Withdrawal Rejected</b>\n\n"
                    f"💰 {w['coins']} points have been "
                    "refunded to your balance.",
                    parse_mode="HTML"
                )

        else:
            await q.message.reply_text(
                "❌ Already processed or not found."
            )


async def run():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing"
        )

    init()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(cb)
    )

    # Number input handlers
    from telegram.ext import MessageHandler, filters

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            withdraw_amount
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_message
        )
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run())
