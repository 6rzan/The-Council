# Deploying The Council (T046 — P3 deployment bonus)

The FastAPI web app is a single container. Locally it binds `127.0.0.1` and
auto-opens a browser; in a container it binds `0.0.0.0:$PORT` (Cloud Run
convention) and runs `uvicorn` directly (no browser). The `GOOGLE_API_KEY` is
supplied at runtime as an env/secret — it is **never** baked into the image
(`.dockerignore` excludes `.env`, per Constitution Principle IV).

## Prerequisites

- The [Google AI Studio API key](https://aistudio.google.com/apikey) (free tier)
- A Google Cloud project with the Artifact Registry and Cloud Run APIs enabled
- `gcloud` CLI authenticated (`gcloud auth login`)

## 1. Build the image

```bash
# set these once
PROJECT_ID=your-gcp-project
REGION=us-central1
REPO=council

# create the Artifact Registry repo (one time)
gcloud artifacts repositories create $REPO \
  --repository-format=docker --location=$REGION

# build & push with Cloud Build (builds in the cloud, no local Docker needed)
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/council:latest
```

Or build locally and push:

```bash
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/council:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/council:latest
```

## 2. Store the API key as a secret

```bash
echo -n "YOUR_AI_STUDIO_KEY" | gcloud secrets create council-google-api-key \
  --data-file=-
gcloud secrets add-iam-policy-binding council-google-api-key \
  --member=serviceAccount:$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

## 3. Deploy to Cloud Run

```bash
gcloud run deploy council \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/council:latest \
  --region=$REGION \
  --port=8080 \
  --min-instances=0 --max-instances=3 \
  --set-secrets=GOOGLE_API_KEY=council-google-api-key:latest \
  --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=FALSE \
  --no-allow-unauthenticated   # require auth, or remove this flag for a public demo URL
```

`--min-instances=0` scales to zero (free-ish idle); the in-memory
`InMemorySessionService` means session state does NOT survive a cold start
(FR-012 — by design, nothing persists beyond a session). For a stateless
deployment this is fine; each page load starts a fresh council.

## 4. Verify

```bash
URL=$(gcloud run services describe council --region=$REGION --format='value(status.url)')
curl -s $URL/healthz        # {"ok":true}
```

Open the URL in a browser and ask a question — the SSE stream works on Cloud Run
(HTTP/1.1 chunked transfer).

## Notes & limits

- **Free-tier rate limits still apply**: the Gemini free tier (~20
  requests/day for `gemini-2.5-flash`) is per API key, not per deployment.
- **No persistence**: this is the in-memory MVP. A persistent
  `DatabaseSessionService` would be needed for session continuity across
  cold starts — out of scope (FR-012).
- **Secrets**: only `GOOGLE_API_KEY` is required; Wikipedia is keyless. The
  `scripts/secret-scan.sh` gate runs in CI to ensure no key is ever committed.
