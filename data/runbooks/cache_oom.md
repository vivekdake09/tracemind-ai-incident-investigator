# Runbook: Redis Cache Memory Exhaustion (OOM)

## Description
This runbook covers scenarios where an in-memory cache store (Redis or Memcached) runs out of available memory (`maxmemory`) and starts failing write requests or evicting critical cache keys.

## Common Symptoms
- Application logs show `OOM command not allowed when used memory > 'maxmemory'` or `Redis::CommandError: OOM`.
- Sudden latency spikes across all services querying the cache due to cache penetration to primary databases.
- High eviction count reported in Redis metrics (`evicted_keys`).

## Troubleshooting Steps
1. **Check Memory Usage**: Run `INFO memory` in Redis CLI. Check `used_memory_human` vs `maxmemory_human`.
2. **Inspect Eviction Policy**: Verify `maxmemory-policy`. If set to `noeviction`, Redis rejects all write operations once limit is reached.
3. **Identify Big Keys & Missing TTL**:
   - Run `redis-cli --bigkeys` to detect oversized keys or large hashes/sets.
   - Sample keys to verify if recently added features set proper TTLs (Time-To-Live).

## Remediation
- Flush transient untracked keys or expired sessions if safe.
- Temporarily scale up Redis instance memory capacity.
- Update application code to enforce explicit TTLs on all newly cached entities.
- Configure appropriate eviction policy (e.g. `volatile-lru` or `allkeys-lru`).
