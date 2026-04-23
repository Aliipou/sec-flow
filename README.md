# sec-flow

> Real-time SEC EDGAR insider transaction monitor with urgency scoring.

[![CI](https://github.com/Aliipou/sec-flow/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/sec-flow/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**sec-flow** queries the SEC EDGAR API for Form 4 insider transactions and XBRL company financials, scoring each transaction by urgency — large purchases, same-day filings, direct holdings — to surface the signals that matter most.

## Features

- **Form 4 scraping**: insider buy/sell transactions from SEC EDGAR full-text search
- **XBRL company facts**: revenue, assets, liabilities for any public company
- **Urgency scoring**: 0–100 composite score (transaction size, filing speed, directness)
- **Dashboard endpoint**: aggregated stats for a given ticker
- **Rate-limit compliant**: `asyncio.Semaphore(5)` + proper `User-Agent` per SEC fair-access policy
- **Docker-ready**: single-container deployment

## Quick Start

```bash
git clone https://github.com/Aliipou/sec-flow
cd sec-flow
pip install -r requirements.txt
SEC_USER_AGENT="yourapp/1.0 your@email.com" uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs)

### Docker

```bash
docker build -t sec-flow .
docker run -p 8000:8000 -e SEC_USER_AGENT="myapp/1.0 me@example.com" sec-flow
```

## API

### `GET /v1/flow/transactions/{ticker}` — Recent Form 4 filings

```bash
curl http://localhost:8000/v1/flow/transactions/AAPL
```

Returns list of insider transactions with urgency scores.

### `GET /v1/flow/company/{cik}` — XBRL company facts

```bash
curl http://localhost:8000/v1/flow/company/0000320193
```

### `GET /v1/flow/dashboard/{ticker}` — Aggregated dashboard

```bash
curl http://localhost:8000/v1/flow/dashboard/AAPL
```

## Urgency Score

| Signal | Points |
|---|---|
| Purchase (not sale) | +40 |
| Transaction value > $1M | +30 |
| Filed same/next day | +20 |
| Direct ownership | +10 |
| **Max** | **100** |

## SEC Fair Access Policy

SEC EDGAR requires a descriptive `User-Agent` header:
```
User-Agent: MyApp/1.0 myemail@domain.com
```

Set this via the `SEC_USER_AGENT` environment variable.

## License

MIT
