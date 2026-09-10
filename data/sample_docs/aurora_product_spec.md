# Aurora Analytics Platform — Product Specification (v3.2)

Aurora is an internal real-time analytics platform built by the (fictional)
company Helios Labs. This document is the canonical reference for what Aurora
does and how it is configured.

## Overview

Aurora ingests event streams, materializes them into queryable rollups, and
serves dashboards with sub-second latency. It is used internally by Helios Labs
product teams and is **not** a public product.

## Architecture

- **Ingest tier** — accepts events over gRPC and Kafka. Default ingest topic is
  `aurora.events.v1`. Maximum accepted event size is **256 KB**.
- **Rollup engine** — windows events into 1s, 1m, 1h, and 1d granularities.
  Rollups are stored in the `aurora_rollups` ClickHouse cluster.
- **Query gateway** — exposes a REST + GraphQL API. The default query timeout is
  **30 seconds**; queries exceeding it are cancelled and return HTTP 504.
- **Dashboard service** — a React front-end that polls the query gateway.

## Configuration defaults

| Setting | Default | Notes |
|---|---|---|
| Retention (raw events) | 14 days | configurable up to 90 days |
| Retention (1d rollups) | 730 days | not configurable |
| Max query concurrency | 64 | per tenant |
| Auth | mTLS + OIDC | OIDC provider is Helios SSO |

## Service-level objectives

- Dashboard p99 query latency: **< 800 ms**.
- Ingest availability: **99.95%** monthly.
- Rollup freshness: 1-minute rollups are available within **5 seconds** of the
  source event.

## Known limitations

- Aurora does not support cross-tenant joins.
- Backfill of historical data is limited to the raw-event retention window.
