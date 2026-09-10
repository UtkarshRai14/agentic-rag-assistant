# Aurora Changelog

## v3.2 (current)
- Raised max event size from 128 KB to **256 KB**.
- Added GraphQL query API alongside REST.
- Default raw-event retention increased from 7 to **14 days**.

## v3.1
- Introduced 1-second rollup granularity.
- Reduced dashboard p99 latency target from 1200 ms to **800 ms**.

## v3.0
- Migrated the rollup store to ClickHouse (`aurora_rollups`).
- Replaced API-key auth with **mTLS + OIDC** (Helios SSO).
- Removed legacy cross-tenant join support (now an explicit non-goal).

## v2.4
- Added Kafka ingest alongside gRPC.
- Raw-event retention configurable up to 90 days.
