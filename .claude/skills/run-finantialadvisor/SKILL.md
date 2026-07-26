---
name: run-finantialadvisor
description: Build, run, and drive finantialAdvisor (the Financial Advisor Streamlit dashboard). Use when asked to start the app, run its tests, take a screenshot of the dashboard, or verify a change works end-to-end in the UI (e.g. "testa no Streamlit se X aparece certo").
---

Financial Advisor is a Python/Streamlit app backed by MongoDB, plus a
Playwright driver at `.claude/skills/run-finantialadvisor/driver.mjs` that
drives the dashboard headlessly (fill ticker → collect+analyze → conclusão →
recomendação → screenshots). Most day-to-day verification during
development actually goes through the **direct-invocation** scripts in
`scripts/` (see below) — reach for the Playwright driver specifically when
you need to confirm the *dashboard* renders a change correctly, not just
that the underlying service logic works.

All paths below are relative to the repo root (`finantialAdvisor/`).

## Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-pip   # only if venv/pip missing
```

Docker (for MongoDB) and Node/npx must already be available — this repo
doesn't install them.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # fill NEWSAPI_KEY / BRAPI_API_TOKEN for full coverage
                        # (optional — collection isolates missing-source failures)

docker compose up -d
python scripts/check_setup.py   # confirms Mongo connection + creates indexes
```

Playwright driver deps (one-time; browser installs to `~/.cache/ms-playwright`,
no sudo needed):

```bash
cd .claude/skills/run-finantialadvisor
npm install
npx playwright install chromium
cd ../../..
```

## Run (agent path)

1. Start Streamlit in the background and wait for it to actually serve:

```bash
source .venv/bin/activate
nohup streamlit run app.py --server.headless true --server.port 8501 \
  > /tmp/run-finantialadvisor-streamlit.log 2>&1 &
timeout 30 bash -c 'until curl -sf http://localhost:8501 >/dev/null; do sleep 1; done'
```

2. Drive it — cadastra um ticker, roda a coleta real (yfinance/brapi.dev/
   NewsAPI), gera Conclusão e Recomendação, tira screenshot em cada etapa:

```bash
node .claude/skills/run-finantialadvisor/driver.mjs [TICKER] [BASE_URL]
# defaults: TICKER=PETR4.SA  BASE_URL=http://localhost:8501
```

Screenshots → `/tmp/run-finantialadvisor/screenshots/{00_home,01_cadastrado,02_coletado,03_conclusao,04_recomendacao}.png`.
Full page text of the two key steps → `02_body.txt` / `04_body.txt` in the
same directory. The driver prints collected browser console errors and
exits non-zero if any were captured.

3. Stop the server (match by full command line — see Gotchas):

```bash
pkill -f "streamlit run app.py --server.headless true --server.port 8501"
```

## Direct invocation (usually the faster path)

Most changes to collectors/analyzers/conclusion/recommendation logic are
verified without the browser at all, straight against Mongo:

```bash
source .venv/bin/activate
python scripts/collect_and_analyze.py PETR4.SA --name "Petrobras"  # coleta + 3 análises
python scripts/build_conclusion.py PETR4.SA                        # síntese
python scripts/build_recommendation.py PETR4.SA                    # veredito final
```

Each prints JSON and exits 1 with a friendly message on error (ticker not
found, insufficient analyses, etc.) — reach for these before the full
Playwright driver.

## Run (human path)

```bash
source .venv/bin/activate
streamlit run app.py   # opens http://localhost:8501, Ctrl-C to stop
```

## Test

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

210 tests, all mocked/fake — no network, no Mongo required.

---

## Gotchas

- **Waiting for `text=Fundamentalista` (or similar) to confirm "Coletar e
  Analisar" finished is a trap.** The sidebar nav already has "Análise
  Fundamentalista" rendered before you even click the button, so that
  selector matches instantly and you screenshot mid-spinner. Wait for the
  spinner text itself (`"Coletando dados e rodando as 3 análises..."`) to
  go **visible then hidden** — waiting for `hidden` alone races: if the
  spinner hasn't rendered yet at the instant you check, "not present" also
  counts as hidden and resolves immediately, before collection even starts.
- **`nohup cmd & echo $!` doesn't reliably capture the Streamlit process
  PID** — Streamlit re-execs itself, so the PID you captured can point at
  an already-exited parent shell while the real process lives under a
  different PID. `kill $(cat pidfile)` then silently does nothing and the
  port stays bound. Stop it with `pkill -f "<the exact launch command>"`
  instead.
- **The dashboard calls real external APIs** (yfinance, brapi.dev, NewsAPI)
  — there's no mock mode. This is expected/by design (see `services/asset_service.py`
  isolation logic), not a driver bug: a source being down or a missing API
  key shows up as a `⚠️` for that one analysis, not a crash. If **all**
  three analyses fail (e.g. no internet), "Gerar Conclusão" shows a red
  `st.error` instead of the success text the driver waits for, and the
  driver's `waitForSelector` will time out — that's a real signal, not a
  flaky selector.
- **`npx playwright install-deps chromium` wants `sudo apt-get`** for a
  handful of font packages (`fonts-freefont-ttf`, etc.). Turned out
  unnecessary — plain `npx playwright install chromium` (browser binary
  only, downloads to `~/.cache/ms-playwright`, no sudo) was enough to
  render and screenshot the dashboard correctly.
- **A new service dependency with a default real repository silently
  pollutes the real Mongo if a test forgets to fake it** — e.g.
  `RecommendationService(analysis_history_service=AnalysisHistoryService())`
  by default, and any test that doesn't override it will really call
  `.record()` (an unconditional upsert) against whatever Mongo the test
  process can reach. The test still passes (no assertion fails), so this
  doesn't show up as a failure — check for it by grepping the new
  constructor param across the test file and confirming every call site
  passes a fake, not by trusting a green run.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'pip'` / venv creation fails**:
  `python3-venv`/`python3-pip` aren't installed. `sudo apt-get install -y
  python3.12-venv python3-pip`, then recreate the venv.
- **Sidebar shows "MongoDB indisponível"**: `docker compose up -d` wasn't
  run, or the container isn't healthy yet — check `docker compose ps`.
- **Driver hangs on `page.goto` / times out on `text=Financial Advisor`**:
  Streamlit isn't actually up yet — the `timeout 30 bash -c 'until curl
  -sf ...'` wait in step 1 wasn't run, or the port is already occupied by
  a stale instance (`pkill -f "streamlit run app.py"` first, then relaunch).
