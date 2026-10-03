# Clipcaps v2

Telegram Bot + Mini App starter for a legitimate reward platform.

## Includes
- Professional Mini App UI
- Telegram bot
- Coin balance
- Daily bonus
- Referral tracking
- bKash/Nagad withdrawal requests
- Admin statistics and withdrawal status
- Idempotent reward events
- Two supplied external SmartLinks

## Monetag
The supplied SmartLinks are exposed only as external offers. They are NOT counted as paid clicks.

For a rewarded-ad earning system, connect the `/reward` endpoint only to Monetag's documented, verified rewarded-ad completion mechanism. Do not credit coins from a client-side click, page open, timer, or unverified request.

## Run
pip install -r requirements.txt

Terminal 1:
export BOT_TOKEN="..."
export ADMIN_ID="..."
export WEBAPP_URL="https://YOUR-DOMAIN"
python -m app.bot

Terminal 2:
uvicorn app.web:app --host 0.0.0.0 --port 8000

Serve `web/index.html` from your HTTPS domain and set that URL in BotFather as the Mini App URL.

## Production security
Before public launch, implement Telegram WebApp initData validation on the server and use the verified Telegram user ID. The sample `/balance` and `/withdraw` endpoints are intentionally simple starter endpoints and should not be considered production-grade authentication.

For a real payout operation, add admin authentication, audit logs, payout reconciliation, rate limits, and PostgreSQL.
