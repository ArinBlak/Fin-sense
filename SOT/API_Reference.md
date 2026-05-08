# FinSense API Reference

**Base URL:** `http://localhost:8000`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger) · `http://localhost:8000/redoc`  
**Auth:** Bearer token — include `Authorization: Bearer <token>` on all protected routes.

---

## Health

| Method | Endpoint  | Auth | Description        |
|--------|-----------|------|--------------------|
| GET    | `/`       | No   | Service info       |
| GET    | `/health` | No   | Health check       |

---

## Auth

### POST `/auth/register`
Create a new account.

**Body**
```json
{
  "email": "user@example.com",
  "username": "arindam",
  "password": "secret123"
}
```
**Response `201`**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "arindam",
  "is_active": true,
  "created_at": "2026-05-09T10:00:00Z"
}
```

---

### POST `/auth/login`
Obtain a JWT access token.

**Body**
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```
**Response `200`**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```
**Errors:** `401` Invalid credentials · `403` Account disabled

---

### GET `/auth/me` 🔒
Return the currently authenticated user.

**Response `200`** — `UserOut` object

---

### DELETE `/auth/me` 🔒
Permanently delete the authenticated user's account.

**Response `204`** No Content

---

## Tickers

All routes require authentication (🔒).

### POST `/tickers`
Add a ticker to track.

**Body**
```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "sector": "Technology"
}
```
**Response `201`** — `TickerOut`  
**Errors:** `400` Ticker already exists

---

### GET `/tickers`
List all tracked tickers.

**Query params:** `skip` (default 0) · `limit` (default 50)  
**Response `200`** — `TickerOut[]`

---

### GET `/tickers/{ticker_id}`
Get a single ticker by ID.

**Response `200`** — `TickerOut`  
**Errors:** `404`

---

### PUT `/tickers/{ticker_id}`
Update company name or sector.

**Body** (all fields optional)
```json
{
  "company_name": "Apple Inc.",
  "sector": "Technology"
}
```
**Response `200`** — `TickerOut`

---

### DELETE `/tickers/{ticker_id}`
Remove a ticker.

**Response `204`**

---

## Transcripts

All routes require authentication (🔒).

### POST `/transcripts/fetch`
Fetch earnings call transcripts from earningscall in the background and persist them to the database.

**Body**
```json
{
  "symbol": "AAPL",
  "years": [2022, 2023, 2024]
}
```
**Response `202`**
```json
{ "message": "Fetching transcripts for AAPL in background" }
```

---

### GET `/transcripts`
List stored transcripts.

**Query params:** `ticker_id` (optional filter) · `skip` · `limit`  
**Response `200`** — `TranscriptOut[]`

---

### GET `/transcripts/{transcript_id}`
Get a single transcript.

**Response `200`** — `TranscriptOut`  
**Errors:** `404`

---

### DELETE `/transcripts/{transcript_id}`
Delete a transcript.

**Response `204`**

---

## Sentiment Analysis

All routes require authentication (🔒). Model is lazy-loaded on first request.

### POST `/sentiment`
Run FinBERT sentiment inference on a piece of text and store the result.

**Body**
```json
{
  "text": "Revenue grew 12% year-over-year driven by strong iPhone sales.",
  "ticker_symbol": "AAPL",
  "transcript_id": null
}
```
**Response `201`**
```json
{
  "id": 1,
  "input_text": "Revenue grew 12% ...",
  "label": "positive",
  "score_positive": 0.9412,
  "score_neutral": 0.0481,
  "score_negative": 0.0107,
  "ticker_id": 1,
  "transcript_id": null,
  "created_at": "2026-05-09T10:05:00Z"
}
```
**Labels:** `positive` · `neutral` · `negative`  
**Errors:** `503` Model not found (run training first)

---

### GET `/sentiment`
List all sentiment results for the authenticated user.

**Query params:** `ticker_id` · `skip` · `limit`  
**Response `200`** — `SentimentOut[]`

---

### GET `/sentiment/{result_id}`
Get a single sentiment result.

**Response `200`** — `SentimentOut`  
**Errors:** `404`

---

### DELETE `/sentiment/{result_id}`
Delete a sentiment result.

**Response `204`**

---

## Training

All routes require authentication (🔒). Training runs in the background as a subprocess.

### POST `/training`
Start a new fine-tuning run. Only one run can be active at a time.

**Body** (all fields optional)
```json
{
  "epochs": 5,
  "batch_size": 16,
  "learning_rate": 2e-5
}
```
**Response `202`** — `TrainingRunOut`
```json
{
  "id": 1,
  "status": "pending",
  "epochs": 5,
  "batch_size": 16,
  "learning_rate": 0.00002,
  "test_accuracy": null,
  "test_f1": null,
  "log_output": null,
  "started_at": null,
  "finished_at": null,
  "created_at": "2026-05-09T10:10:00Z"
}
```
**Errors:** `409` A run is already in progress

---

### GET `/training`
List all training runs (newest first).

**Query params:** `skip` · `limit`  
**Response `200`** — `TrainingRunOut[]`

---

### GET `/training/latest`
Get the most recent training run.

**Response `200`** — `TrainingRunOut`  
**Errors:** `404`

---

### GET `/training/{run_id}`
Get a training run by ID. Poll this to check status.

**Response `200`** — `TrainingRunOut`

**Status values:** `pending` → `running` → `completed` | `failed`

---

## Data Models

### UserOut
| Field       | Type     |
|-------------|----------|
| id          | int      |
| email       | string   |
| username    | string   |
| is_active   | bool     |
| created_at  | datetime |

### TickerOut
| Field        | Type     |
|--------------|----------|
| id           | int      |
| symbol       | string   |
| company_name | string?  |
| sector       | string?  |
| created_at   | datetime |

### TranscriptOut
| Field      | Type     |
|------------|----------|
| id         | int      |
| ticker_id  | int      |
| year       | int      |
| quarter    | int      |
| text       | string   |
| created_at | datetime |

### SentimentOut
| Field          | Type            |
|----------------|-----------------|
| id             | int             |
| input_text     | string          |
| label          | positive/neutral/negative |
| score_positive | float           |
| score_neutral  | float           |
| score_negative | float           |
| ticker_id      | int?            |
| transcript_id  | int?            |
| created_at     | datetime        |

### TrainingRunOut
| Field         | Type                              |
|---------------|-----------------------------------|
| id            | int                               |
| status        | pending/running/completed/failed  |
| epochs        | int                               |
| batch_size    | int                               |
| learning_rate | float                             |
| test_accuracy | float?                            |
| test_f1       | float?                            |
| log_output    | string?                           |
| started_at    | datetime?                         |
| finished_at   | datetime?                         |
| created_at    | datetime                          |

---

## Error Format

All errors return:
```json
{ "detail": "Human-readable error message" }
```

| Code | Meaning               |
|------|-----------------------|
| 400  | Bad request / duplicate |
| 401  | Missing or invalid token |
| 403  | Forbidden             |
| 404  | Not found             |
| 409  | Conflict              |
| 503  | Service unavailable (model not loaded) |
