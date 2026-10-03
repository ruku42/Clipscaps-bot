import asyncio
from datetime import date
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,WebAppInfo
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,ContextTypes
from app.config import *
from app.db import *

def menu():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("🚀 Open Clipcaps",web_app=WebAppInfo(url=WEBAPP_URL))],
      [InlineKeyboardButton("🎁 Daily Bonus",callback_data="daily"),InlineKeyboardButton("💰 Balance",callback_data="balance")],
      [InlineKeyboardButton("🔗 Offers",callback_data="offers")]
    ])
async def start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    u=update.effective_user; ref=None
    if ctx.args:
        try: ref=int(ctx.args[0])
        except: pass
    upsert(u.id,u.username or "",u.first_name or "",ref,REFERRAL_BONUS)
    r=user(u.id)
    await update.message.reply_text(
      f"✨ <b>Welcome to Clipcaps</b>, {u.first_name}!

"
      f"💰 Balance: <b>{r['coins']}</b> coins
"
      f"🎁 Daily bonus: <b>+{DAILY_BONUS}</b>

"
      "Open the Mini App to manage your rewards.",
      parse_mode="HTML",reply_markup=menu())
async def cb(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    if q.data=="balance":
        r=user(uid); await q.message.reply_text(f"💰 Balance: {r['coins']} coins")
    elif q.data=="daily":
        ok=daily(uid,str(date.today()),DAILY_BONUS)
        await q.message.reply_text("🎁 +%d coins added!"%DAILY_BONUS if ok else "⏳ Daily bonus already claimed.")
    elif q.data=="offers":
        kb=InlineKeyboardMarkup([
          [InlineKeyboardButton("🎁 Offer 1",url=SMARTLINK_1)],
          [InlineKeyboardButton("⭐ Offer 2",url=SMARTLINK_2)]])
        await q.message.reply_text("📢 External offers
Choose only offers that are relevant to you.",reply_markup=kb)
async def run():
    if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    init(); app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start)); app.add_handler(CallbackQueryHandler(cb))
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()
if __name__=="__main__": asyncio.run(run())
