# Runbook: Authentication Failures

## Description
Runbook for diagnosing and resolving authentication failures, particularly those related to JWTs and 401 Unauthorized errors on API endpoints.

## Common Symptoms
- Spike in 401 Unauthorized errors across clients.
- Logs indicating "Invalid signature for JWT" or "Token expired".
- Users reporting being logged out unexpectedly.

## Troubleshooting Steps
1. **Check Key Rotation**: Was the JWT signing key recently rotated? If so, verify that all API instances have pulled the new key.
2. **Check Time Sync**: Ensure NTP is synced on the servers. Clock drift can cause tokens to appear prematurely expired or issued in the future.
3. **Verify Auth Service Health**: Check if the centralized authentication service (e.g., Auth0, Cognito, or internal auth service) is down or degraded.
4. **Inspect Token Payloads**: Decode a sample failed token to ensure the `iss` (issuer) and `aud` (audience) claims match expected values.

## Remediation
- If the key was rotated, perform a rolling restart of API pods to ensure they load the latest keys from the secret store.
- Re-sync clocks if drift is detected.
- Roll back to the previous key if the new key is improperly formatted or deployed.
