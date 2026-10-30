# SchemeMatch

A local-first government scheme discovery application with a React + TypeScript frontend, FastAPI backend, and MongoDB catalogue.

Scheme records and authoritative eligibility rules are stored in MongoDB. Entries without enough rules or profile information remain **Unknown** and are never presented as eligible. The app does not make an official eligibility decision.

## Run locally

Requirements: Node.js 20+, Python 3.10+, and a MongoDB database containing a `schemes` collection.

1. Configure `MONGODB_URI`, `DATABASE_NAME`, and `JWT_SECRET_KEY` in `backend/.env`. Keep this file private; it is ignored by git.
2. Start the API:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --port 8001
   ```

3. In a second terminal, start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

4. Open the local URL printed by Vite (normally `http://localhost:5173`).

Use `python seed_mongo.py` to load the small starter catalogue. For MongoDB Atlas, allow your development machine's IP in Network Access and ensure the database user has read/write access. Passwords containing URI-reserved characters such as `@` must be URL encoded. The API reports a service error if MongoDB is unavailable; it does not silently switch data stores. One MongoClient is reused by the API process and closed at shutdown.

The Required Scheme Finder loads `BAAI/bge-m3` through `sentence-transformers` on first use and stores scheme embeddings in the local persistent ChromaDB directory (`backend/.chroma` by default). Set `CHROMA_PERSIST_DIRECTORY` in `backend/.env` to change the storage location. The model may require a one-time download. Missing BGE-M3 or ChromaDB dependencies return an explicit service error; the finder does not silently replace semantic search with a keyword fallback.

## Modules and API

- **Discover:** fetches the registered user's saved profile and compares it against every MongoDB scheme. It displays all schemes whose recorded mandatory eligibility rules match, with benefits, explanations, documents, application instructions, and official links. It does not semantically rank or cap the results.
- **Eligibility Scan:** shows all eligible, unknown, unverified, and ineligible schemes using the same rule engine.
- **Required Scheme Finder:** filters to the selected category (or all categories), then applies recorded eligibility rules before semantic retrieval. The five highest-ranked eligible schemes use BGE-M3 + ChromaDB with configurable 60/25/15 default weights (semantic/category-objective/benefit). Missing or incomplete eligibility stays in a separate Unknown group.
- **LLM Scheme Reasoning:** available from the app navigation and `/llm-reasoning`; it uses the same category and eligibility-first finder, returns up to five matches, and provides a profile- and objective-specific LLM reason with source quotes verified against each scheme record. Benefits, key documents, and the first application step are shown on each result. Provider/model configuration is available to administrators at `/admin`.
- **Trust Scores:** displays a transparent score based on source domain, HTTPS, attribution, verification recency, and stored content completeness. It is not a guarantee of accuracy, eligibility, or approval.
- `GET /api/users/me/eligible-schemes`, `GET /api/users/me/eligibility-scan`, `POST /api/users/me/scheme-finder`, and `GET /api/trust-scores`.
- `POST /api/recommendations` is retained for compatibility and returns all rule-eligible schemes without semantic ranking.
- `POST /api/eligibility/check`, `GET /api/schemes`, `GET /api/schemes/{scheme_id}`, `GET /api/categories`, and `GET /api/health`.

Finder relevance scores indicate content relevance, not probabilities of eligibility or approval. The LLM explains only the top eligible, retrieved schemes using the search request and saved profile context; evidence quotes are checked against the stored MongoDB records before they are returned.

## RAG LLM provider configuration

The scheme-finder RAG layer uses one provider-neutral LLM interface. Provider selection and model names can be changed in the authenticated admin panel at `/admin`; credentials and custom endpoint URLs remain backend-only environment variables and are never stored in MongoDB or returned by the API. The admin settings page displays only whether the selected credential is configured and offers a connection test.

Set the selected provider's variables in `backend/.env` (or in the backend process environment):

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=
GOOGLE_API_KEY=
ANTHROPIC_API_KEY=
LLM_BASE_URL=
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Supported `LLM_PROVIDER` values are `openai`, `google`, `anthropic`, `openai_compatible`, and `ollama`. Only the selected cloud provider's key is read: OpenAI uses `OPENAI_API_KEY`, Gemini uses `GOOGLE_API_KEY`, and Claude uses `ANTHROPIC_API_KEY`. For an OpenAI-compatible service, set `LLM_PROVIDER=openai_compatible`, `LLM_BASE_URL` to its API root, and `OPENAI_API_KEY` to that service's credential. The default OpenAI-compatible model is `openai/gpt-oss-120b`; use a model identifier supported by the selected endpoint. Ollama requires no API key and uses `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`).

Provider/model selections made in the admin panel are stored in MongoDB's `app_settings` collection, without secrets, and take precedence over `LLM_PROVIDER`/`LLM_MODEL` defaults. Set or rotate credentials in the backend environment, then restart the backend. Do not paste keys into source files, frontend settings, commits, or chat; revoke any key that has been exposed.

The finder sends the search request, saved profile context, and only the top five schemes that passed recorded MongoDB eligibility rules and were retrieved by BGE-M3/ChromaDB to the explanation provider. The response must be valid structured JSON with exact scheme IDs and source quotes; fabricated or ungrounded evidence is rejected. LLM configuration, timeout, authentication, rate-limit, and quota failures are returned explicitly rather than replaced with unverified explanations. BGE-M3 embeddings and ChromaDB retrieval remain independent of provider selection.

Run backend tests from `backend`:

```powershell
python -m pytest
```
