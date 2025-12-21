# Service Level Agreements (SLAs)

This document defines the performance targets (SLAs) for SkillMeat. All components must meet these targets to ensure a responsive and reliable user experience.

## Overview

Performance SLAs are defined for three main components:
- **API Endpoints**: Backend REST API response times
- **Core Operations**: System-level operations (bundle export/import, MCP health checks)
- **Web UI**: Frontend page load times and interactivity

## API Performance Targets

All API latency measurements are in milliseconds (ms).

| Endpoint | P95 Latency | P99 Latency | Description |
|----------|-------------|-------------|-------------|
| `/api/marketplace/listings` | <200ms | <500ms | List marketplace offerings |
| `/api/marketplace/listings/{id}` | <100ms | <300ms | Get single listing details |
| `/api/marketplace/install` | <3000ms | <5000ms | Install bundle from marketplace |
| `/api/marketplace/publish` | <5000ms | <10000ms | Publish listing to marketplace |
| `/api/mcp/health` | <200ms | <500ms | Check MCP server health |
| `/api/mcp/servers` | <200ms | <500ms | List MCP servers |
| `/api/sharing/export` | <1500ms | <3000ms | Export artifact bundle |
| `/api/sharing/import` | <1500ms | <3000ms | Import artifact bundle |
| `/api/collections` | <200ms | <500ms | List collections |
| `/api/collections/{id}` | <100ms | <300ms | Get collection details |
| `/api/collections/{id}/artifacts` | <200ms | <500ms | List artifacts in collection |
| `/api/analytics/usage` | <300ms | <800ms | Get usage statistics |
| `/api/analytics/top-artifacts` | <200ms | <500ms | Get top artifacts |
| `/health` | <50ms | <100ms | API health check |

### API Performance Notes

- **P95**: 95% of requests complete within this time
- **P99**: 99% of requests complete within this time
- Measurements exclude network latency (localhost testing)
- Targets assume moderate system load (≤100 concurrent users)
- All endpoints should return appropriate HTTP status codes within these targets
- Error responses should be as fast as successful responses

## Core Operations Targets

Operations are measured by mean execution time over multiple iterations.

| Operation | Mean Time Target | Description |
|-----------|------------------|-------------|
| Bundle Export | <2000ms | Export 1-10 artifacts to bundle |
| Bundle Import | <2000ms | Import bundle to collection |
| MCP Health Check | <500ms | Check all MCP server health |
| Collection List | <1000ms | List all artifacts in collection |
| Collection Search | <1000ms | Search artifacts (≤50 results) |
| Artifact Add | <500ms | Add single artifact to collection |

### Operations Performance Notes

- Targets assume standard collection size (10-100 artifacts)
- Bundle operations scale with artifact count and size
- Search performance depends on index size and query complexity
- MCP health checks run in parallel across servers

## Web UI Performance Targets

Frontend performance is measured using Core Web Vitals and Lighthouse metrics.

### Lighthouse Scores

| Metric | Target | Description |
|--------|--------|-------------|
| Performance Score | ≥90 | Overall Lighthouse performance |
| Accessibility Score | ≥90 | Overall accessibility compliance |

### Core Web Vitals

| Metric | Target | Category | Description |
|--------|--------|----------|-------------|
| First Contentful Paint (FCP) | <1.5s | Loading | First text/image paint |
| Largest Contentful Paint (LCP) | <2.5s | Loading | Largest content element visible |
| Time to Interactive (TTI) | <3.5s | Loading | Page becomes fully interactive |
| Cumulative Layout Shift (CLS) | <0.1 | Visual Stability | Visual stability score |
| First Input Delay (FID) | <100ms | Interactivity | Response to first user input |
| Time to First Byte (TTFB) | <600ms | Server Response | Initial server response |

### Page-Specific Targets

| Page | FCP Target | LCP Target | Notes |
|------|------------|------------|-------|
| Homepage (/) | <1.5s | <2.5s | Initial load |
| Marketplace (/marketplace) | <1.5s | <2.5s | List view |
| Collections (/collections) | <1.5s | <2.5s | Dashboard view |
| Listing Detail | <1.2s | <2.0s | Single item view |

### Interactive Elements

| Interaction | Target | Description |
|-------------|--------|-------------|
| Search Response | <1s | Marketplace/collection search |
| Page Navigation | <500ms | Between pages (with Next.js prefetch) |
| Button Click Response | <100ms | Interactive feedback |
| Form Submission | <2s | Form validation and submit |

### Web UI Performance Notes

- Measurements taken on desktop Chrome (mid-tier hardware)
- Targets assume good network conditions (3G or better)
- Next.js optimizations (prefetching, code splitting) enabled
- Images should use next/image for optimization
- Critical CSS inlined, non-critical deferred

## Load Testing Targets

System performance under concurrent load.

| Scenario | Concurrent Users | RPS (Requests/Second) | Error Rate Target |
|----------|------------------|------------------------|-------------------|
| Browse Marketplace | 100 | 50 | <1% |
| Search Listings | 50 | 25 | <1% |
| Install Bundles | 20 | 5 | <2% |
| Health Checks | 200 | 100 | <0.5% |
| Mixed Workload | 100 | 40 | <1.5% |

### Load Testing Notes

- Tests simulate realistic user behavior patterns
- Wait times between requests: 1-3 seconds
- Error rate includes both HTTP errors and timeouts
- System should gracefully degrade under overload
- Rate limiting may affect results (100 req/hour/IP for API)

## Resource Limits

Hard limits on resource consumption.

| Resource | Limit | Rationale |
|----------|-------|-----------|
| Max Bundle Size | 100 MB | Reasonable download size |
| Max Artifacts per Bundle | 1000 | Performance/practicality balance |
| API Rate Limit (General) | 100 req/hour/IP | Prevent abuse |
| API Rate Limit (Install/Publish) | 10 req/hour/IP | Heavy operations |
| Max Collection Size | 10,000 artifacts | Database/performance limit |
| Max Search Results | 1000 | Pagination required |
| Max Concurrent MCP Servers | 50 | System resource limit |

## Monitoring and Alerting

### Performance Monitoring

Performance metrics are continuously monitored:

- **API Latency**: P50, P95, P99 response times
- **Error Rates**: 4xx, 5xx response rates
- **Throughput**: Requests per second
- **Resource Usage**: CPU, memory, disk I/O
- **Web Vitals**: Real User Monitoring (RUM) data

### SLA Violation Alerts

Alerts are triggered when:

- P95 latency exceeds target by >20% for 5 minutes
- P99 latency exceeds target by >50% for 5 minutes
- Error rate exceeds target for 3 consecutive minutes
- Any endpoint P95 >2x target
- Core Web Vitals degrade by >30% from baseline

### Performance Testing Cadence

- **Pre-commit**: Unit performance tests (pytest-benchmark)
- **PR Validation**: API benchmark suite
- **Weekly**: Full load testing (Locust)
- **Release**: Complete performance regression suite
- **Monthly**: Lighthouse audits and Web Vitals analysis

## Performance Budget

To prevent performance regression, we enforce a performance budget:

### JavaScript Bundle Size

| Bundle | Target | Maximum |
|--------|--------|---------|
| Initial JS | <150 KB | 200 KB |
| Total JS (all chunks) | <500 KB | 750 KB |
| Third-party JS | <100 KB | 150 KB |

### Asset Size

| Asset Type | Target | Maximum |
|------------|--------|---------|
| Images (per image) | <100 KB | 200 KB |
| CSS | <50 KB | 75 KB |
| Fonts | <100 KB | 150 KB |

### Performance Budget Enforcement

- Webpack bundle analyzer run on each build
- CI fails if bundle size exceeds maximum
- Lighthouse CI prevents merging if performance score drops >5 points
- Bundle size increase >10% requires performance review

## Testing Tools

The following tools are used to verify SLA compliance:

### Backend Performance

- **pytest-benchmark**: Unit-level operation benchmarks
- **Locust**: Load testing and concurrent user simulation
- **Custom benchmark scripts**: API endpoint latency measurement
- **Python benchmark_api.py**: Automated API endpoint testing
- **Python benchmark_operations.py**: Core operation benchmarking

### Frontend Performance

- **Lighthouse**: Overall performance and accessibility scoring
- **Playwright + Web Vitals**: Core Web Vitals measurement
- **Chrome DevTools**: Performance profiling
- **Next.js Analytics**: Real User Monitoring

### CI/CD Integration

- **GitHub Actions**: Automated performance testing on PR and weekly
- **Performance regression detection**: Compare against baseline
- **SLA compliance checker**: Verify all metrics meet targets
- **Automated reporting**: Performance dashboard and trends

## Baseline Performance

Current baseline measurements (as of implementation):

| Category | Measurement | Status |
|----------|-------------|--------|
| API P95 (average) | TBD | ⏳ Pending |
| Operations (average) | TBD | ⏳ Pending |
| Lighthouse Performance | TBD | ⏳ Pending |
| LCP (average) | TBD | ⏳ Pending |

Baselines will be established during Phase 5 performance testing.

## Performance Optimization Strategies

If SLAs are not met, consider:

### Backend Optimizations

1. **Database Indexing**: Ensure proper indexes on frequently queried fields
2. **Caching**: Implement Redis/in-memory caching for hot paths
3. **Query Optimization**: Reduce N+1 queries, use batch loading
4. **Async Processing**: Move heavy operations to background tasks
5. **Connection Pooling**: Optimize database connection management
6. **API Response Compression**: Enable gzip/brotli compression

### Frontend Optimizations

1. **Code Splitting**: Split bundles at route level
2. **Image Optimization**: Use WebP format, lazy loading, srcset
3. **Prefetching**: Use Next.js prefetch for navigation
4. **CSS Optimization**: Inline critical CSS, defer non-critical
5. **Component Optimization**: Use React.memo, useMemo, useCallback
6. **Service Worker**: Implement offline caching strategies

### Infrastructure Optimizations

1. **CDN**: Serve static assets via CDN
2. **Load Balancing**: Distribute load across multiple servers
3. **Horizontal Scaling**: Add more API server instances
4. **Database Scaling**: Read replicas, sharding if needed
5. **Resource Limits**: Set appropriate CPU/memory limits

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-17 | Initial SLA definitions for Phase 5 |

## References

- [Core Web Vitals](https://web.dev/vitals/)
- [Lighthouse Performance Scoring](https://web.dev/performance-scoring/)
- [API Performance Best Practices](https://restfulapi.net/performance/)
- [Next.js Performance](https://nextjs.org/docs/advanced-features/measuring-performance)

---

For questions or concerns about these SLAs, please contact the SkillMeat development team.
