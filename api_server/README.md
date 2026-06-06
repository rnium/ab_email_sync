# API Documentation — Actual Budget Sync API

## Overview

This service provides a small HTTP API that proxies and validates calls to the `@actual-app/api` client. It exposes a versioned REST surface under `/api/v1` with the endpoints described below.

Server implementation lives in `src/` (TypeScript, ESM). The service performs input validation with Zod and returns the full objects returned by the Actual API client.

## Quick start

1. Copy the example env file and fill values:

   ```sh
   cp .env.example .env
   # edit .env and set ACTUAL_SERVER_URL, ACTUAL_PASSWORD, ACTUAL_SYNC_ID
   ```

2. Development (run TypeScript directly):

   ```sh
   npm run dev
   ```

3. Build for production and run compiled files:

   ```sh
   npm run build
   npm start
   ```

4. Default data directory (on Linux):

   - If `ACTUAL_DATA_DIR` is not set, the server uses `${HOME}/.local/share/actual-budget`.
   - The server creates the directory before connecting to Actual.

## Environment variables

- `ACTUAL_SERVER_URL` (required) — Actual server URL (e.g. `http://localhost:5006`).
- `ACTUAL_PASSWORD` (required) — Password for the Actual server.
- `ACTUAL_SYNC_ID` (required) — Budget sync ID (Settings → Advanced → Sync ID).
- `ACTUAL_BUDGET_PASSWORD` (optional) — Budget password if the budget is end-to-end encrypted.
- `ACTUAL_DATA_DIR` (optional) — Override the default data directory.
- `PORT` (optional) — HTTP port (default `3000`).
- `NODE_ENV` (optional) — `development` or `production`.

If any required environment variables are missing the server fails fast with a descriptive error:

```
Missing required environment variable(s): ACTUAL_SERVER_URL, ACTUAL_PASSWORD, ACTUAL_SYNC_ID
Copy .env.example to .env and fill in the values.
```

## Base path

All endpoints are mounted under:

```
/api/v1
```

## Endpoints

All examples assume `http://localhost:3000/api/v1` as the base URL.

### GET /accounts

- Description: Returns all accounts.
- HTTP: `GET /api/v1/accounts`
- Response: `{ data: APIAccountEntity[] }`

APIAccountEntity fields (returned):
- `id` (string)
- `name` (string)
- `offbudget` (boolean | undefined)
- `closed` (boolean | undefined)
- `balance_current` (number | null | undefined)

Example curl:

```sh
curl -s http://localhost:3000/api/v1/accounts | jq
```

### GET /payees

- Description: Returns all payees.
- HTTP: `GET /api/v1/payees`
- Response: `{ data: APIPayeeEntity[] }`

APIPayeeEntity fields (returned):
- `id` (string)
- `name` (string)
- `transfer_acct` (string | undefined)

Example curl:

```sh
curl -s http://localhost:3000/api/v1/payees | jq
```

### GET /category-groups

- Description: Returns category groups. Optional query parameter `hidden` filters by hidden state.
- HTTP: `GET /api/v1/category-groups[?hidden=true|false]`
- Query validation: `hidden` accepts `true` or `false` strings and is transformed to a boolean before passing to the Actual client.
- Response: `{ data: APICategoryGroupEntity[] }`

APICategoryGroupEntity fields (returned):
- `id` (string)
- `name` (string)
- `is_income` (boolean)
- `hidden` (boolean)
- `categories` (APICategoryEntity[] | undefined)

Example curl:

```sh
# all groups
curl -s http://localhost:3000/api/v1/category-groups | jq
# only visible groups
curl -s "http://localhost:3000/api/v1/category-groups?hidden=false" | jq
```

### POST /accounts/:accountId/transactions/import

- Description: Import transactions into an account using Actual's import logic (reconciliation, payee learning, etc.).
- HTTP: `POST /api/v1/accounts/:accountId/transactions/import`
- Path params:
  - `accountId` (string) — required
- Body (JSON) schema (validated):
  - `transactions` (array, required) — list of transaction objects (see fields below). Each transaction object may include:
    - `date` (string, required) — `YYYY-MM-DD`
    - `amount` (integer, optional) — see [Amount format](#amount-format) below
    - `payee` (string | null, optional) — payee id
    - `payee_name` (string, optional) — name for a new/auto-assigned payee
    - `imported_payee` (string, optional)
    - `category` (string, optional)
    - `notes` (string, optional)
    - `imported_id` (string, optional) — external unique id to prevent duplicates
    - `transfer_id` (string, optional)
    - `cleared` (boolean, optional)
    - `subtransactions` (array, optional) — each with `amount` (integer, required) and optional `category`, `notes`
  - `opts` (object, optional):
    - `defaultCleared` (boolean)
    - `dryRun` (boolean)
    - `reimportDeleted` (boolean)

#### Amount format

Amounts are provided as integers or floats. The server converts them to Actual's internal integer format with `Math.round(amount * 100)`, then divides by 100 on the way back out. This applies to transaction amounts and subtransaction amounts alike.

| You send | Calculation | Stored in Actual | Returned to you |
|---|---|---|---|
| `1201` | `1201 × 100` | `120100` | `1201` |
| `-1102` | `-1102 × 100` | `-110200` | `-1102` |
| `-1201.676` | `round(-1201.676 × 100)` = `round(-120167.6)` | `-120168` | `-1201.68` |
| `99.999` | `round(99.999 × 100)` = `round(9999.9)` | `10000` | `100` |
| `0` | `0 × 100` | `0` | `0` |

Notes:
- The `account` property is injected server-side from the `:accountId` parameter; clients must not include `account` in the transaction objects.
- Dates are strictly validated to `YYYY-MM-DD` format.
- Amounts accept any number (integer or float). The rounding step means precision beyond 2 decimal places is lost.

Response: `{ data: ImportTransactionsResult }` where `ImportTransactionsResult` contains:
- `added`: `string[]` — IDs of newly added transactions
- `updated`: `string[]` — IDs of updated transactions
- `updatedPreview`: Array of preview objects (each contains `transaction`, optional `existing`, `ignored`, `tombstone`). `transaction.amount` and `existing.amount` are in the scaled-down form (÷ 100).
- `errors`: Array of `{ message: string }` describing any errors encountered

Example request:

```sh
curl -X POST http://localhost:3000/api/v1/accounts/ACCOUNT_ID/transactions/import \
  -H 'Content-Type: application/json' \
  -d '{
    "transactions": [
      {
        "date": "2024-05-10",
        "amount": -1299,
        "payee_name": "Example Merchant",
        "imported_id": "bank-12345",
        "cleared": true
      }
    ],
    "opts": { "defaultCleared": true }
  }'
```

Example response (successful import):

```json
{
  "data": {
    "added": ["uuid-1"],
    "updated": [],
    "updatedPreview": [],
    "errors": []
  }
}
```

### Validation and error responses

- Validation failures (bad path/query/body) return `400` with a JSON body containing Zod's flattened errors:

```json
{
  "error": {
    "message": "Validation failed",
    "details": {
      "fieldErrors": { "transactions": ["At least one transaction is required"] },
      "formErrors": []
    }
  }
}
```

- If the Actual client has not been initialized or the server fails to connect, the startup process fails with a descriptive message. At runtime if the API call fails, a `5xx` will be returned with the underlying message.

- If the server is started without required environment variables the process fails immediately with a helpful message calling out missing variables.

## Amount conversion

All transaction amounts pass through `src/utils/amount.ts`:

- `toActualAmount(n)` — `Math.round(n * 100)` before sending to the Actual API; handles both integers and floats, rounding to 2 decimal places of precision
- `fromActualAmount(n)` — `n / 100` before returning in responses

This conversion is applied in `src/services/transactionsService.ts` to top-level transaction amounts and every subtransaction amount, both on input and on response (`updatedPreview` objects).

## Implementation notes & files

- Core server: `src/server.ts`
- Express app and routing: `src/app.ts`, `src/routes/` (routes are versioned under `src/routes/v1`)
- Actual client wrapper and lifecycle: `src/actual/client.ts`
- Validation: `src/validation/` (Zod schemas) and `src/middleware/validate.ts`
- Controllers: `src/controllers/*Controller.ts`
- Services that call `@actual-app/api`: `src/services/*Service.ts`
- Middleware: `src/middleware/asyncHandler.ts`, `src/middleware/errorHandler.ts`

## Testing tips

- Use the `dev` script to run the TypeScript entry point with `tsx` so you can iterate quickly (`npm run dev`).
- When testing the import endpoint, prefer `dryRun: true` initially to validate results without modifying the budget.
- If the Actual server uses self-signed TLS, follow Actual's docs to configure Node TLS (e.g. `NODE_EXTRA_CA_CERTS` or `NODE_TLS_REJECT_UNAUTHORIZED` for local testing).

## Security

- Do not commit `.env` or any secrets. The `.env.example` file documents required variables only.
- This service is intended to run in a trusted environment that has network access to your Actual server. Put it behind proper network/firewall controls if used in production.