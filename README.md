# Blockchain Analyzer

An end-to-end blockchain transaction analytics MVP featuring ingestion, tracing, anomaly detection, clustering, and compliance alerting backed by Neo4j and FastAPI with a React visual console.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers (trace, alerts, compliance, etc.)
│   │   ├── db/              # Neo4j driver bootstrap
│   │   ├── ingest/          # Etherscan ingestion pipeline
│   │   ├── ml/              # IsolationForest anomaly scoring
│   │   ├── models/          # Shared Pydantic schemas
│   │   └── utils/           # Clustering, addresses, compliance helpers
│   ├── main.py              # FastAPI application entrypoint
│   ├── requirements.txt     # Locked backend dependencies
│   └── .env.template        # Sample environment variables
├── frontend/
│   ├── index.html
│   ├── package.json         # Vite + React + Tailwind setup
│   └── src/
│       ├── App.jsx          # Root SPA shell
│       ├── api.js           # REST client
│       └── components/      # Trace and Alerts views
├── data/
│   └── sample_txns.json     # Example Ethereum transactions
├── docs/
│   └── slides.md            # Demo deck outline
└── README.md
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Neo4j 5.x (Aura, Desktop, or Docker)
- An Etherscan API key

## Backend Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.template .env
```

Update `.env` with your credentials:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
ETHERSCAN_API_KEY=your-etherscan-key
```

### Start Neo4j Locally (Docker)

```powershell
docker run --rm -it -p7474:7474 -p7687:7687 -e NEO4J_AUTH=neo4j/your-password neo4j:5.20.0
```

### Launch the API

```powershell
uvicorn app.main:app --reload --port 8000
```

Key endpoints:

- `GET /health` – readiness
- `GET /ingest/{address}` – pull transactions from Etherscan and persist to Neo4j
- `POST /trace` – shortest-path tracing with hop limits
- `POST /alerts/refresh` – recompute IsolationForest scores
- `GET /alerts` – high-risk addresses with severity
- `GET /address/{addr}` – cluster metadata
- `POST /compliance/blacklist` – upload CSV of sanctioned addresses

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev -- --open
```

Configure `VITE_API_URL` in a `.env` file within `frontend/` if the backend is not running on `http://127.0.0.1:8000`.

The UI includes:

- **Trace Explorer** – visualize address graphs with Cytoscape.js
- **Alerts Dashboard** – sortable alert table with CSV export
- **Compliance Controls** – ingest blacklists and recompute severities

## Analytics Pipeline Overview

1. **Ingestion** – `GET /ingest/{address}` fetches transactions via Etherscan and builds graph relationships in Neo4j.
2. **Clustering** – `POST /address/cluster` labels connected components with `cluster_id` metadata.
3. **Anomaly Detection** – `POST /alerts/refresh` computes risk scores using IsolationForest features (volume, velocity, counterparties).
4. **Compliance** – `POST /compliance/blacklist` flags sanctioned wallets and bumps alert severity.
5. **Visualization** – React dashboard renders clusters, anomalies, and compliance alerts.

## Testing

```powershell
cd backend
pytest
```

Tests mock Neo4j interactions and validate `/health`, `/trace`, and `/alerts` endpoints.

## Deployment Notes

- The backend is stateless and can run behind any ASGI server (Gunicorn + Uvicorn workers recommended for production).
- Ensure Neo4j connectivity and credentials are available in the runtime environment.
- Configure rate limiting or caching for Etherscan if operating under heavy load.

## License

MIT License © 2025 Blockchain Analyzer contributors.