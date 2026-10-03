import sqlite3
from pathlib import Path
DB=Path("clipcaps.db")
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    c=db(); c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
      coins INTEGER NOT NULL DEFAULT 0, referred_by INTEGER,
      daily_claim TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS withdrawals(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
      method TEXT, number TEXT, coins INTEGER, amount_bdt REAL,
      status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS reward_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
      event_id TEXT UNIQUE, reward INTEGER, source TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS referrals(
      referrer_id INTEGER, referred_id INTEGER UNIQUE,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """); c.commit(); c.close()
def user(uid):
    c=db(); r=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone(); c.close(); return r
def upsert(uid,username,first_name,ref=None,refbonus=100):
    c=db(); old=c.execute("SELECT id FROM users WHERE id=?",(uid,)).fetchone()
    if old: c.execute("UPDATE users SET username=?,first_name=? WHERE id=?",(username,first_name,uid))
    else:
        valid=ref if ref and ref!=uid and c.execute("SELECT id FROM users WHERE id=?",(ref,)).fetchone() else None
        c.execute("INSERT INTO users(id,username,first_name,referred_by) VALUES(?,?,?,?)",(uid,username,first_name,valid))
        if valid:
            c.execute("INSERT OR IGNORE INTO referrals(referrer_id,referred_id) VALUES(?,?)",(valid,uid))
            c.execute("UPDATE users SET coins=coins+? WHERE id=?",(refbonus,valid))
    c.commit(); c.close()
def add(uid,n):
    c=db(); c.execute("UPDATE users SET coins=coins+? WHERE id=?",(n,uid)); c.commit(); c.close()
def daily(uid,today,reward):
    c=db(); r=c.execute("SELECT daily_claim FROM users WHERE id=?",(uid,)).fetchone()
    if not r or r["daily_claim"]==today: c.close(); return False
    c.execute("UPDATE users SET coins=coins+?,daily_claim=? WHERE id=?",(reward,today,uid)); c.commit(); c.close(); return True
def reward_once(uid,event_id,reward,source):
    c=db()
    try:
        c.execute("INSERT INTO reward_events(user_id,event_id,reward,source) VALUES(?,?,?,?)",(uid,event_id,reward,source))
        c.execute("UPDATE users SET coins=coins+? WHERE id=?",(reward,uid)); c.commit(); ok=True
    except sqlite3.IntegrityError: ok=False
    c.close(); return ok
def withdraw(uid,method,number,coins,amount):
    c=db(); c.execute("UPDATE users SET coins=coins-? WHERE id=?",(coins,uid))
    c.execute("INSERT INTO withdrawals(user_id,method,number,coins,amount_bdt) VALUES(?,?,?,?,?)",(uid,method,number,coins,amount))
    c.commit(); c.close()
def withdrawals(status="pending"):
    c=db(); rows=c.execute("SELECT * FROM withdrawals WHERE status=? ORDER BY id DESC",(status,)).fetchall(); c.close(); return rows
def set_status(wid,status):
    c=db(); c.execute("UPDATE withdrawals SET status=? WHERE id=?",(status,wid)); c.commit(); c.close()
def stats():
    c=db()
    users=c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    coins=c.execute("SELECT COALESCE(SUM(coins),0) n FROM users").fetchone()["n"]
    pending=c.execute("SELECT COUNT(*) n FROM withdrawals WHERE status='pending'").fetchone()["n"]
    paid=c.execute("SELECT COALESCE(SUM(amount_bdt),0) n FROM withdrawals WHERE status='paid'").fetchone()["n"]
    c.close(); return users,coins,pending,paid
