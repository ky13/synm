# synm
Personal AI vault + mediator. See "Personal AI Vault on Ollama — Architecture Blueprint" for design.

## Quickstart
1) `cp .env.example .env && edit MEDIATOR_PAT`
2) `docker compose up -d`
3) `make seed`
4) Try the CPI:
   - `curl -H "Authorization: Bearer $MEDIATOR_PAT" -X POST http://localhost:8080/v1/session`
   - `curl -H "Authorization: Bearer $MEDIATOR_PAT" -H "Content-Type: application/json" -d '{"session_id":"<from previous>","profile":"work","scopes":["bio.basic","projects.recent"],"prompt":"Draft a short bio","max_tokens":800}' http://localhost:8080/v1/context`

## Assumptions
- Local dev uses PAT auth; mTLS optional later.
- Default deny for PII unless explicitly allowed.