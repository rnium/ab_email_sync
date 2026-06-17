# AB Email Sync

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
git clone https://github.com/rnium/ab_email_sync.git
cd ab_email_sync
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
| `GITHUB_SSO_CLIENT_ID` | *(optional)* GitHub OAuth app client ID — enables "Sign in with GitHub" (see [GitHub SSO](#optional-github-sso-login)) |
| `GITHUB_SSO_CLIENT_SECRET` | *(optional)* GitHub OAuth app client secret |
| `GITHUB_SSO_ALLOWABLE_DOMAINS` | *(optional)* Comma-separated email domains allowed to sign in via GitHub (default: `gmail.com`) |

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

The admin UI will be available at `http://localhost:8088`.

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

## (Optional) GitHub SSO login

By default the admin login page shows the usual **username & password** form. You can additionally enable a **"Sign in with GitHub"** button. This is entirely optional — if the credentials below are not set, the GitHub button is automatically hidden and only the username/password form is shown.

### 1. Create a GitHub OAuth app

1. Go to **GitHub → Settings → Developer settings → [OAuth Apps](https://github.com/settings/developers) → New OAuth App** (for an organisation, use the org's developer settings instead).
2. Fill in:
   - **Application name** — anything, e.g. `AB Email Sync`
   - **Homepage URL** — where the app is hosted, e.g. `http://localhost:8000`
   - **Authorization callback URL** — `<your-host>/github_sso/callback/`
     (e.g. `http://localhost:8000/github_sso/callback/`)
3. Click **Register application**, then **Generate a new client secret**.
4. Copy the **Client ID** and **Client secret**.

### 2. Add the credentials

In `backend/.env`:

```env
GITHUB_SSO_CLIENT_ID=your_client_id
GITHUB_SSO_CLIENT_SECRET=your_client_secret
# Optional: restrict which email domains may sign in (default: gmail.com)
GITHUB_SSO_ALLOWABLE_DOMAINS=gmail.com
```

Restart the backend so the new settings are picked up:

```bash
docker compose up -d --build backend
```

The GitHub button will now appear on the login page.

### 3. Note on user accounts

Auto-creation of users is **disabled** — signing in with GitHub does **not** create a new account. The GitHub account's verified email must:

- match the email of an **existing Django user** (create one via `createsuperuser` or the **Users** admin), and
- belong to one of the domains in `GITHUB_SSO_ALLOWABLE_DOMAINS`.

If either condition fails, the sign-in is rejected.

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
