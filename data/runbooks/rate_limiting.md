# Runbook: Upstream Rate Limiting and HTTP 429 Errors

## Description
This runbook covers diagnosing and remediating API failures resulting from hitting upstream vendor or internal service rate limits, manifest by HTTP status 429 (Too Many Requests).

## Common Symptoms
- Upstream HTTP calls returning status code 429.
- Error messages indicating `Rate limit exceeded`, `Too Many Requests`, or `Quota exhausted`.
- Sudden spike in failed outbound webhooks or payment authorization requests.

## Troubleshooting Steps
1. **Inspect Response Headers**: Check upstream headers such as `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining`.
2. **Detect Retry Storms**: Determine if the calling service is looping immediate retries without exponential backoff or jitter.
3. **Check Client Concurrency**: Verify if multiple workers or async batch jobs are hitting the endpoint concurrently without rate throttling.

## Remediation
- Implement exponential backoff with full jitter on all external API HTTP clients.
- Add client-side rate limiters (e.g. token bucket or leaky bucket algorithm).
- Implement circuit breakers to fail fast when downstream services indicate persistent throttling.
- Request rate limit increases from the external API provider if traffic is legitimate business volume.
