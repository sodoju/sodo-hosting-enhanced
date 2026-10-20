# SODO HOSTING — Telegram Hosting Bot

Premium Telegram bot for hosting Python/Node.js projects, with credits, referrals,
force-join verification, and a full owner admin panel.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL database
- Git (for GitHub deployment feature)
- Railway account

### 2. Installation
```bash
git clone <your-repo-url>
cd sodo_hosting
pip install -r requirements.txt
```

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | From @BotFather |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `WELCOME_CREDITS` | | Default: 50 |
| `DAILY_REWARD_CREDITS` | | Default: 10 |
| `REFERRAL_REWARD_CREDITS` | | Default: 25 |
| `FREE_PLAN_MAX_PROJECTS` | | Default: 1 |
| `FREE_PLAN_MAX_FILE_SIZE_MB` | | Default: 1 |
| `STORAGE_BASE_PATH` | | Default: /tmp/sodo_projects |

### 4. Get Your Owner ID
Message @userinfobot on Telegram — it returns your numeric Telegram ID.

### 5. Database Setup

Railway PostgreSQL or external Postgres. The bot auto-creates tables on first start
via `create_tables()` in `post_init`.

For migration management (production):
```bash
alembic upgrade head
```

### 6. Deploy on Railway

1. Create a Railway project
2. Add a PostgreSQL service — copy the `DATABASE_URL`
3. Set all environment variables in Railway Variables tab
4. Push your code — Railway auto-deploys
5. The `Procfile` defines `bot` and `worker` processes

### 7. Configure Force Join

In the bot:
1. Open Admin Panel (`/start` → ⚙️ Admin Panel)
2. Go to 🔐 Force Join Settings
3. Tap ➕ Add Channel
4. Enter: `CHAT_ID Display Name @username`

**Bot must be an administrator** of private channels for membership checks.
For public channels, username alone is sufficient.

### 8. Admin Panel Access

Only the Telegram account matching `OWNER_ID` can access the Admin Panel.
Authorization is verified server-side on every callback — not just at menu entry.

### 9. Hosting Architecture

```
Telegram Bot (Railway)
      │
      ▼
Bot Process (bot/main.py)
      │ reads/writes
      ▼
PostgreSQL (Railway)
      │ project files
      ▼
File Storage (STORAGE_BASE_PATH)
      │ subprocess.Popen / asyncio.subprocess
      ▼
User Project Runtimes
```

**Security warning**: This embedded subprocess runner is for trusted projects and
light workloads only. User processes receive a small allowlist of runtime
environment variables plus their project-specific variables; host secrets are
not copied into the process environment. This is defense in depth, **not a
sandbox**: projects still run under the same operating-system account and may
access files, processes, and resources available to that account. Do not expose
this setup to untrusted users or treat environment filtering as tenant isolation.
Before accepting untrusted code, replace `hosting_service.py`'s subprocess
runner with a properly isolated container or external worker (non-root, resource
limits, filesystem/network controls, and per-tenant secrets).

### 10. Running Tests
```bash
pip install -r requirements.txt
python -m pytest -v
```

GitHub Actions runs the test suite and Python compilation checks on every push
and pull request.

### 11. Troubleshooting

**Bot not responding**: Check `BOT_TOKEN` is valid and only one polling instance runs.

**DB connection failed**: Ensure `DATABASE_URL` starts with `postgresql://` or `postgres://`
(the bot converts it to asyncpg format automatically).

**Force join not working**: Bot must be able to call `getChatMember` — it needs to be
admin in private channels. For public channels it only needs to be a member.

**Project fails to start**: Check `STORAGE_BASE_PATH` is writable. Subprocess requires
Python or Node.js to be installed on the server.

---

## File Structure
```
sodo_hosting/
├── bot/
│   ├── main.py              # Application entry point
│   ├── config.py            # Environment configuration
│   ├── database.py          # Async SQLAlchemy engine
│   ├── models/              # ORM models (User, Project, Credits…)
│   ├── services/            # Business logic layer
│   ├── handlers/            # Telegram update handlers
│   │   └── admin/           # Owner-only admin handlers
│   ├── keyboards/           # Inline keyboard builders
│   └── utils/               # Decorators, validators, formatters
├── worker/                  # Background worker process
├── tests/                   # pytest test suite
├── migrations/              # Alembic migration environment
├── requirements.txt
├── Procfile
├── railway.json
└── .env.example
```
