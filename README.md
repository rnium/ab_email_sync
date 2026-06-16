# AB Email Transaction

Automatically imports bank transactions from Gmail into [Actual Budget](https://actualbudget.org/) by parsing email notifications and syncing them via the Actual Budget API.

## How it works

1. **Scheduler** — runs on a configurable interval, fetches unread emails from Gmail that match your bank notification patterns.
2. **Parser** — extracts transaction type (debit/credit/transfer) and amount from email subjects/bodies using per-bank regex rules.
3. **Importer** — pushes the parsed transactions into Actual Budget via a local API bridge.
4. **Admin UI** — a Django admin interface to manage bank accounts, parsing rules, configuration, and view sync logs.

## Services

| Service | Description |
|---|---|
| `api_server` | Node.js bridge between the Django backend and the Actual Budget server |
| `backend` | Django app — admin UI, migrations, static files (port 8000) |
| `scheduler` | Runs `fetch-sync` on a timed loop; interval is configurable from the admin UI |

## Requirements

- Docker and Docker Compose
- A running [Actual Budget](https://actualbudget.org/) server
- A Gmail account with bank notification emails
- Gmail OAuth credentials (see setup below)

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/rnium/ab_email_transaction.git
cd ab_email_transaction
```

Copy the env files and fill in your values:

```bash
cp backend/.env.example backend/.env
cp api_server/.env.example api_server/.env
```

**`backend/.env`**

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key (generate a long random string) |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames, or `*` |
| `ACTUAL_API_SERVER_URL` | URL of the `api_server` service (default: `http://api_server:3000` in Docker) |
| `EMAIL_MAX_AGE` | How many days back to fetch emails (default: `1`) |
| `EMAIL_MAX_RESULTS` | Max emails to fetch per run (default: `1000`) |

**`api_server/.env`**

| Variable | Description |
|---|---|
| `ACTUAL_SERVER_URL` | URL of your Actual Budget server |
| `PORT` | Port the bridge listens on (default: `3000`) |

### 2. Prepare the database file

The SQLite database is bind-mounted from the host so it persists across container rebuilds:

```bash
touch backend/db.sqlite3
```

### 3. Start the stack

```bash
docker compose up -d --build
```

The admin UI will be available at `http://localhost:8000`.

### 4. Create a superuser

```bash
docker compose exec backend python manage.py createsuperuser
```

### 5. Configure via the admin UI

Navigate to **System → Configuration** and fill in:

- **Actual Budget Password** — your Actual Budget server password
- **Actual Budget Sync ID** — the budget sync ID from Actual Budget
- **Gmail Credential JSON** — paste the contents of your OAuth credentials JSON file (downloaded from Google Cloud Console)

Then set up **Bank Accounts** and their **Email Parsing Rules** to match your bank's notification emails.

### 6. Authenticate Gmail

Run the OAuth flow once on your local machine (a browser will open):

```bash
docker compose exec -it backend python manage.py gmail_auth
# or, if running outside Docker:
python manage.py gmail_auth
```

The token is saved to the database and refreshed automatically from that point on.

## Scheduler intervals

The scheduler interval is configurable live from the admin UI under **System → Configuration**:

| Key | Default | Description |
|---|---|---|
| Daytime start hour | `8` | Hour when daytime interval begins (0–23) |
| Daytime end hour | `23` | Hour when daytime interval ends (0–23) |
| Daytime interval | `5` | Minutes between runs during the day |
| Nighttime interval | `15` | Minutes between runs at night |

Changes take effect on the next tick — no restart needed.

## Development

Run the backend locally:

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirement.txt
python manage.py migrate
python manage.py seed_configurations
python manage.py createsuperuser
python manage.py runserver
```

## License

MIT — see [LICENSE](LICENSE).
