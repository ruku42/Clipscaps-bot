import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://YOUR-DOMAIN.example"
)

# Withdrawal
MIN_WITHDRAW_COINS = int(
    os.getenv("MIN_WITHDRAW_COINS", "1000")
)

# 1 coin/point = 0.50 BDT
COIN_TO_BDT = float(
    os.getenv("COIN_TO_BDT", "0.50")
)

DAILY_BONUS = int(
    os.getenv("DAILY_BONUS", "50")
)

REFERRAL_BONUS = int(
    os.getenv("REFERRAL_BONUS", "100")
)

# Daily Tasks
TASK_REWARD = 10
TASK_WAIT_SECONDS = 8

SMARTLINK_1 = "https://omg10.com/4/11942844"
SMARTLINK_2 = "https://omg10.com/4/11942845"
SMARTLINK_3 = "https://omg10.com/4/11950217"
SMARTLINK_4 = "https://omg10.com/4/11950215"
SMARTLINK_5 = "https://omg10.com/4/11950214"

TASKS = [
    ("task1", "🎁 Task 1", SMARTLINK_1),
    ("task2", "🎁 Task 2", SMARTLINK_2),
    ("task3", "🎁 Task 3", SMARTLINK_3),
    ("task4", "🎁 Task 4", SMARTLINK_4),
    ("task5", "🎁 Task 5", SMARTLINK_5),
]
