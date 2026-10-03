import sqlite3
from pathlib import Path

DB = Path("clipcaps.db")


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    c = db()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        coins INTEGER NOT NULL DEFAULT 0,
        referred_by INTEGER,
        daily_claim TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS withdrawals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        method TEXT,
        number TEXT,
        coins INTEGER,
        amount_bdt REAL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS reward_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_id TEXT UNIQUE,
        reward INTEGER,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS referrals(
        referrer_id INTEGER,
        referred_id INTEGER UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS task_claims(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id TEXT NOT NULL,
        claim_date TEXT NOT NULL,
        reward INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, task_id, claim_date)
    );
    """)

    c.commit()
    c.close()


def user(uid):
    c = db()
    r = c.execute(
        "SELECT * FROM users WHERE id=?",
        (uid,)
    ).fetchone()
    c.close()
    return r


def upsert(uid, username, first_name, ref=None, refbonus=100):
    c = db()

    old = c.execute(
        "SELECT id FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    if old:
        c.execute(
            """
            UPDATE users
            SET username=?, first_name=?
            WHERE id=?
            """,
            (username, first_name, uid)
        )

    else:
        valid = (
            ref
            if ref
            and ref != uid
            and c.execute(
                "SELECT id FROM users WHERE id=?",
                (ref,)
            ).fetchone()
            else None
        )

        c.execute(
            """
            INSERT INTO users(
                id, username, first_name, referred_by
            )
            VALUES(?,?,?,?)
            """,
            (uid, username, first_name, valid)
        )

        if valid:
            c.execute(
                """
                INSERT OR IGNORE INTO referrals(
                    referrer_id, referred_id
                )
                VALUES(?,?)
                """,
                (valid, uid)
            )

            c.execute(
                """
                UPDATE users
                SET coins=coins+?
                WHERE id=?
                """,
                (refbonus, valid)
            )

    c.commit()
    c.close()


def add(uid, n):
    c = db()

    c.execute(
        """
        UPDATE users
        SET coins=coins+?
        WHERE id=?
        """,
        (n, uid)
    )

    c.commit()
    c.close()


def daily(uid, today, reward):
    c = db()

    r = c.execute(
        "SELECT daily_claim FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    if not r or r["daily_claim"] == today:
        c.close()
        return False

    c.execute(
        """
        UPDATE users
        SET coins=coins+?, daily_claim=?
        WHERE id=?
        """,
        (reward, today, uid)
    )

    c.commit()
    c.close()

    return True


def task_claim(uid, task_id, today, reward):
    c = db()

    try:
        c.execute(
            """
            INSERT INTO task_claims(
                user_id, task_id, claim_date, reward
            )
            VALUES(?,?,?,?)
            """,
            (uid, task_id, today, reward)
        )

        c.execute(
            """
            UPDATE users
            SET coins=coins+?
            WHERE id=?
            """,
            (reward, uid)
        )

        c.commit()
        ok = True

    except sqlite3.IntegrityError:
        c.rollback()
        ok = False

    c.close()
    return ok


def task_claimed(uid, task_id, today):
    c = db()

    r = c.execute(
        """
        SELECT id
        FROM task_claims
        WHERE user_id=?
        AND task_id=?
        AND claim_date=?
        """,
        (uid, task_id, today)
    ).fetchone()

    c.close()

    return r is not None


def reward_once(uid, event_id, reward, source):
    c = db()

    try:
        c.execute(
            """
            INSERT INTO reward_events(
                user_id, event_id, reward, source
            )
            VALUES(?,?,?,?)
            """,
            (uid, event_id, reward, source)
        )

        c.execute(
            """
            UPDATE users
            SET coins=coins+?
            WHERE id=?
            """,
            (reward, uid)
        )

        c.commit()
        ok = True

    except sqlite3.IntegrityError:
        c.rollback()
        ok = False

    c.close()
    return ok


def withdraw(uid, method, number, coins, amount):
    c = db()

    try:
        r = c.execute(
            "SELECT coins FROM users WHERE id=?",
            (uid,)
        ).fetchone()

        if not r or r["coins"] < coins:
            c.close()
            return False

        c.execute(
            """
            UPDATE users
            SET coins=coins-?
            WHERE id=?
            """,
            (coins, uid)
        )

        c.execute(
            """
            INSERT INTO withdrawals(
                user_id, method, number,
                coins, amount_bdt
            )
            VALUES(?,?,?,?,?)
            """,
            (
                uid,
                method,
                number,
                coins,
                amount
            )
        )

        c.commit()
        ok = True

    except Exception:
        c.rollback()
        ok = False

    c.close()
    return ok


def withdrawals(status="pending"):
    c = db()

    rows = c.execute(
        """
        SELECT *
        FROM withdrawals
        WHERE status=?
        ORDER BY id DESC
        """,
        (status,)
    ).fetchall()

    c.close()
    return rows


def get_withdrawal(wid):
    c = db()

    r = c.execute(
        """
        SELECT *
        FROM withdrawals
        WHERE id=?
        """,
        (wid,)
    ).fetchone()

    c.close()
    return r


def set_status(wid, status):
    c = db()

    r = c.execute(
        """
        SELECT user_id, coins, status
        FROM withdrawals
        WHERE id=?
        """,
        (wid,)
    ).fetchone()

    if not r:
        c.close()
        return False

    if r["status"] != "pending":
        c.close()
        return False

    if status == "rejected":
        c.execute(
            """
            UPDATE users
            SET coins=coins+?
            WHERE id=?
            """,
            (r["coins"], r["user_id"])
        )

    c.execute(
        """
        UPDATE withdrawals
        SET status=?
        WHERE id=?
        """,
        (status, wid)
    )

    c.commit()
    c.close()

    return True


def stats():
    c = db()

    users = c.execute(
        "SELECT COUNT(*) n FROM users"
    ).fetchone()["n"]

    coins = c.execute(
        """
        SELECT COALESCE(SUM(coins),0) n
        FROM users
        """
    ).fetchone()["n"]

    pending = c.execute(
        """
        SELECT COUNT(*) n
        FROM withdrawals
        WHERE status='pending'
        """
    ).fetchone()["n"]

    paid = c.execute(
        """
        SELECT COALESCE(SUM(amount_bdt),0) n
        FROM withdrawals
        WHERE status='paid'
        """
    ).fetchone()["n"]

    c.close()

    return users, coins, pending, paid
