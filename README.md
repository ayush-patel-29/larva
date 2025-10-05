Space Biology Knowledge Engine (Larva)

Full-stack project for exploring NASA bioscience research with a semantic search API, a Neo4j-powered knowledge graph, and a Next.js visualization dashboard.

## Overview

- Backend (`backend/`): Flask API that
  - Loads NASA bioscience articles from `nasa_articles_scraped_20251004_070858.json`
  - Indexes text in ChromaDB with `SentenceTransformer('all-MiniLM-L6-v2')` for semantic search
  - Builds and queries a Neo4j knowledge graph (remote-only) for entities/relations and graph stats
  - Optional AI endpoints using Groq for summaries, topic clustering, insights, sentiment

- Frontend (`frontend/`): Next.js app that
  - Shows dashboard stats and AI insights
  - Renders an interactive D3 knowledge graph (`app/components/KnowledgeGraph.tsx`)
  - Lets you inspect entity details and related articles

## Quickstart

### 1) Backend

Requirements: Python 3.10+, valid remote Neo4j instance, optional Groq API key.

1. Create a `.env` file in `backend/` with your credentials:
   ```
   NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<your-password>
   GROQ_API_KEY=<optional-groq-key>
   GROQ_MODEL=llama-3.1-8b-instant
   ```

2. Install dependencies and run:
   ```bash
   cd backend
   pip install -r requirements.txt
   python app.py
   ```

   The API will initialize embeddings, create a Chroma collection, and connect to Neo4j. On first run it may build the graph from the articles JSON.

3. Key API endpoints (default base: `http://localhost:5000/api`):
   - `GET /health` – server health
   - `GET /stats` – basic corpus stats
   - `GET /articles?page=1&per_page=10&has_results=true|false` – paginated articles
   - `POST /search` – semantic search `{ query, top_k }`
   - `POST /search/keywords` – keyword search `{ keywords[], match_all }`
   - Knowledge graph:
     - `GET /knowledge-graph`
     - `GET /knowledge-graph/entity/:name`
     - `GET /knowledge-graph/communities`
   - AI (requires `GROQ_API_KEY`):
     - `POST /ai/summarize` `{ article_id }`
     - `GET /ai/topics`
     - `GET /ai/insights`
     - `POST /ai/ask` `{ question }`
     - `GET /ai/sentiment`

Notes:
- Neo4j is enforced as remote-only; local URIs are rejected. Use AuraDB or a remote Neo4j.
- The dataset file path is configured in `backend/app.py` as `DATA_FILE`.

### 2) Frontend

Requirements: Node 18+.

1. Configure API base (optional). The frontend defaults to `http://localhost:5000/api`. To override, set `NEXT_PUBLIC_API_BASE` in an `.env.local` under `frontend/`:
   ```
   NEXT_PUBLIC_API_BASE=https://your-backend-host/api
   ```

2. Install and run:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open the app at `http://localhost:3000` to view the dashboard and interactive graph.

## Tech Stack

- Backend: Flask, ChromaDB, Sentence-Transformers, Neo4j Python Driver, Groq SDK
- Frontend: Next.js (App Router), React 18, D3, Recharts, Tailwind CSS 4

## Repository Layout

- `backend/app.py` – Flask API server and initialization
- `backend/knowledge_graph.py` – Neo4j graph builder and query utilities
- `backend/ai_services.py` – Groq-based AI helpers with fallbacks
- `backend/requirements.txt` – Python dependencies
- `backend/nasa_articles_*.json` – scraped NASA articles used to build/search
- `frontend/app/page.tsx` – Main dashboard page
- `frontend/app/components/KnowledgeGraph.tsx` – D3 force-directed visualization
- `frontend/app/components/AnalyticsPanel.tsx` – Insights/topics/stats panel

## Development Tips

- First run can take longer while embeddings are computed and the graph is built.
- If graph endpoints return empty, the backend auto-attempts to rebuild importance/relationships and, if needed, the whole graph.
- Groq endpoints gracefully fall back to heuristic outputs if the model call fails or no key is provided.

## License

MIT


