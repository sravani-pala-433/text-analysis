# Textualize-Demo

A FastAPI-powered text analytics service that ingests spreadsheet data, generates semantic embeddings for every piece of text, and lets you **explore the corpus as an interactive 3D point cloud** — where each point is a document positioned by semantic similarity. Points are color-coded by creator and can be filtered by arbitrary attributes.

## Highlights

- **End-to-end demo flow** — register → create a TextSet → upload an Excel file → watch it process → visualize in 3D
- **Semantic search** over text using PGvector cosine/euclidean distance
- **384-dim sentence embeddings** (`all-MiniLM-L6-v2`) reduced to 3 components via PCA for visualization
- **Async file processing** with a Watchdog-based file observer (chunked `.xls` / `.xlsx` ingestion)
- **Served demo UI** at `/` (stands in for the external S3-hosted frontend)

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| ORM / migrations | SQLAlchemy 2.x + Alembic |
| Database | PostgreSQL with the `pgvector` extension |
| Embeddings | `fastembed` (ONNX Runtime) — `all-MiniLM-L6-v2`, PCA via `scikit-learn` |
| Auth | JWT (HS256, 1h expiry), Argon2 password hashing |
| File ingestion | Watchdog observer + pandas / openpyxl |
| Frontend | Single-page HTML/JS + Three.js (3D), SheetJS (sample file) |
| Infra | Docker + docker-compose |

## Getting started

### 1. Install dependencies

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure environment

Copy your settings into `.env`:

```
DATABASE_URL = "postgresql://user:pass@host/db_name?sslmode=require"
SECRET_KEY = "your-secret-key"
```

The database must have the `pgvector` extension available (e.g. Neon, Supabase, or a local Postgres with `CREATE EXTENSION vector;`).

### 3. Run the server

```bash
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

> First startup can take ~30s while the sentence-transformers model loads.

| Resource | URL |
|---|---|
| Demo UI | http://localhost:8000/ |
| Swagger UI | http://localhost:8000/api/docs |
| ReDoc | http://localhost:8000/api/redoc |
| OpenAPI schema | http://localhost:8000/api/openapi.json |

### Docker

```bash
docker compose up --build
# served at http://localhost:7000/
```

## Deployment

> **Vercel cannot host this backend.** It bundles all Python dependencies into
> a serverless function, which blows past Vercel's size limits. The app also
> needs a long-running watchdog process and a writable disk for model caching,
> which serverless functions don't provide.
>
> Note: embeddings now use **`fastembed` (ONNX Runtime)** instead of
> PyTorch/sentence-transformers. The image is ~150 MB and peak RAM is ~300 MB,
> so even 512 MB free-tier containers (Koyeb, SnapDeploy, etc.) can host it.

The supported setup splits the app in two:

| Component | Host | What it runs |
|---|---|---|
| Backend (FastAPI + ML) | A Docker host (HF Spaces / Render / Railway / Fly.io) | Docker image from `Dockerfile` |
| Frontend (`static/`) | **Vercel** | Static Vite build |

The `Dockerfile` now starts uvicorn on `$PORT` (default `7000`), so any
platform that injects a `PORT` variable works.

### Backend → Render (free plan)

Render still offers a **Free** web-service plan (750 hours/month, auto-deploy
from GitHub, **no credit card required**). Docker image builds are supported.

1. Push the repo to GitHub.
2. Render → New → Web Service → connect the repo. The project is auto-detected
   as Docker (`Dockerfile` present).
3. In the plan dropdown, choose **Free** ($0/month) — not the "Starter" tier,
   which Selects paid by default.
4. Set the environment variables:
   - `DATABASE_URL` (Postgres with the `pgvector` extension — e.g. Neon free tier)
   - `SECRET_KEY`
5. Deploy and wait for the Docker build. URL looks like
   `https://textualize-backend.onrender.com/api/docs`.

**Known free-tier behavior (fine for a demo):**
- The service sleeps after ~15 minutes of inactivity and cold-starts in
  30–60 s on the next request (the small ONNX model (~25 MB) re-downloads/caches on boot).
- Ephemeral disk: uploaded files are processed in `/tmp` and moved to
  `completed/`/`failed/` — nothing needs to survive a restart.
- 750 instance-hours/month (~31 days of always-on, or less with wake-ups).

> Failed on Render before? Make sure the plan is genuinely **Free** and that
> `DATABASE_URL` / `SECRET_KEY` are set — the image build itself is free.

### Local machine + tunnel (zero account, zero cost)

Run the backend locally and expose it with Cloudflare's free tunnel:

```bash
$env:UPLOAD_FILE_DIR = "$PWD\data"   # writable local dir
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
# in a second terminal:
cloudflared tunnel --url http://localhost:8000
```

Cloudflared prints a public `https://...trycloudflare.com` URL to use as the
frontend's `VITE_API_BASE`. No account, no card, no build. The URL changes each
run — fine for a one-off demo. Download the binary from
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

#### Other paid hosts (if you'd rather not babysit a laptop)

Deploy the same `Dockerfile` to **Railway**, **Fly.io**, or the Render paid
plans (~$5–7/month). `render.yaml` (Docker runtime + 5 GB disk) is included for
Render Blueprint deploys.

### Frontend → Vercel

1. In Vercel, import the same GitHub repo. `vercel.json` forces the **Vite** framework with `npm run build` → output `dist`, so the Python files at the root don't confuse the detector.
2. **No zero-config backend deployment** — Vercel only serves the static UI.
3. Add a build-time environment variable in Vercel:
   - `VITE_API_BASE=https://your-backend-url` (your HF Space / Render / tunnel URL)
   The URL is injected into the page during `vite build`, so the UI calls your backend instead of the same origin.
4. CORS is already open (`allow_origins=["*"]`), so cross-origin API calls work.

During local development the frontend falls back to the same origin
(`window.location.origin`), so `npm run dev` (with the `/api` proxy) or simply
serving `static/` from FastAPI keeps working unchanged.

## Demo flow

The UI at `/` walks through the whole pipeline as a 5-step wizard.

1. **Register** — create an account (`POST /api/signup`), then sign in (`POST /api/login`, JWT stored in the browser).
2. **Create TextSet** — a container for a corpus of documents (`POST /api/TextSets`).
3. **Upload File** — upload an Excel file. Use the built-in **⬇ Download Sample Excel File** button to grab a ready-made example.
4. **Processing** — the UI polls `GET /api/TextItems/{text_set_id}` until rows appear; the file observer parses rows, creates attributes, and computes embeddings in the background.
5. **Visualize** — each document becomes a point in 3D space (from its PCA-reduced embedding). Filter by:

   - free-text **search** (substring match)
   - **Numeric** attribute ranges (min / max)
   - **Select** attributes (multi-choice checkboxes)
   - **Text** attributes (substring match) — filters are applied server-side via `POST /api/TextItem/search`

   Hover any point to see the document content; points are color-coded by creator (legend in the corner). Hold mouse to pause auto-rotation; scroll to zoom.

## Upload file format

The file observer expects `.xls` or `.xlsx` with these **first six columns**:

| Column | Description |
|---|---|
| `creator_id` | Author identifier (string) |
| `creator_name` | Author display name |
| `text_content` | The text to embed and analyze |
| `post_date` | ISO-8601 timestamp as text, e.g. `2025-11-01T09:12:00` |
| `external_item_id` | Optional external reference |
| `parent_external_item_id` | Optional parent reference |

Every column from the **7th column onward** is treated as an attribute, with the header formatted as `AttributeName|Type`:

| Header example | Type | Resulting filter |
|---|---|---|
| `Sentiment\|Select` | Select | Checkbox list of distinct values |
| `Rating\|Numeric` | Numeric | Min/max range slider |
| `Region\|Text` | Text | Free-text substring filter |

> Select values may use `|` to denote multiple choices per cell.

## API reference

All API routes require a `Bearer` JWT except `signup`, `login`, and `swaggerlogin`. See `/api/docs` for interactive testing.

### Authentication — `user_controller`

| Method | Path | Description |
|---|---|---|
| POST | `/api/signup` | Register `{user_name, email, password}` |
| POST | `/api/swaggerlogin` | OAuth2 password form login (for Swagger) |
| POST | `/api/login` | JSON login `{username, password}` → `{access_token, user_id, name}` |
| POST | `/api/verifylogin` | Validate the current Bearer token |

### TextSet management — `textset_controller`

| Method | Path | Description |
|---|---|---|
| POST | `/api/TextSets` | Create a TextSet `{title, description}` |
| POST | `/api/TextSets/search` | Search TextSets (title, ids, dates; paginated) |
| POST | `/api/TextItem/search` | Search TextItems (ids, creators, dates, **attributes**; paginated) |
| POST | `/api/TextValue/Search` | Distinct text values for an attribute |
| GET | `/api/TextSets` | List the caller's TextSets |
| GET | `/api/TextSets/{id}/attributes` | List a TextSet's attributes |
| GET | `/api/TextItems/{text_set_id}` | List items (includes `pca_vector` for 3D) |
| POST | `/api/TextSets/{id}/items/search` | Semantic similarity search (euclidean/cosine) |

### File management — `feed_controller`

| Method | Path | Description |
|---|---|---|
| POST | `/api/TextSet/{text_set_id}/upload-file/` | Multipart upload (`file` field) → queued to the file observer |

### Application — `app_controller`

| Method | Path | Description |
|---|---|---|
| GET | `/` , `/index.html` | Serve the demo UI (local `static/index.html`, falling back to `PUBLIC_HTML_URL`) |

## Project structure

```
.
├── main.py                       # FastAPI app, lifespan (file observer), routers
├── static/
│   └── index.html                # Demo UI (single page, 3D visualization)
├── textAnalysisService/
│   ├── auth/
│   │   ├── config/               # settings, DB engine, logging
│   │   ├── controllers/          # route definitions (user, textset, feed, app)
│   │   ├── models.py             # SQLAlchemy models (RegisteredUser, TextSet, ...)
│   │   ├── schema.py             # Pydantic request/response models
│   │   ├── repositories/         # data access layer
│   │   ├── services/             # business logic (auth, textset, embeddings)
│   │   └── utils/                # JWT, file observer, parsers
│   └── textSet/                  # (empty package placeholder)
└── tokenizer/
    └── embedings.py              # sentence embeddings + PCA reduction
```


