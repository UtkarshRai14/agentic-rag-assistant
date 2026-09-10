# Aurora — Frequently Asked Questions

**Q: What is the maximum event size Aurora accepts?**
256 KB. Larger events are rejected at the ingest tier with a 413 error.

**Q: How long are raw events retained?**
14 days by default, configurable up to 90 days. Daily rollups are kept for 730
days and that value cannot be changed.

**Q: Why is my query returning HTTP 504?**
The query exceeded the default 30-second query-gateway timeout. Narrow the time
range or reduce the cardinality of your group-by.

**Q: Does Aurora support cross-tenant joins?**
No. Cross-tenant joins are an explicit non-goal. Each tenant is fully isolated.

**Q: How fresh are the 1-minute rollups?**
1-minute rollups are available within 5 seconds of the source event.

**Q: How do I authenticate?**
Aurora uses mTLS plus OIDC. The OIDC provider is Helios SSO. Personal access
tokens are not supported.

**Q: What database backs the rollups?**
A ClickHouse cluster named `aurora_rollups`.
