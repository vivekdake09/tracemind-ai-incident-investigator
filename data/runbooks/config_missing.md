# Runbook: Missing Configuration and Startup Errors

## Description
This runbook covers scenarios where an application service fails during initialization or container startup due to missing environment variables, config maps, or secret injections.

## Common Symptoms
- Container crashes immediately upon startup (CrashLoopBackOff in Kubernetes).
- Application logs show `KeyError`, `ConfigurationException`, `ValueError: Environment variable not set`, or `Required config missing`.
- Health check endpoints fail to respond on container startup.

## Troubleshooting Steps
1. **Inspect Pod/Container Environment**:
   - Check if required environment variables are injected via Helm values or Kubernetes ConfigMaps.
   - Run `kubectl describe pod <pod_name>` and inspect the `Environment` section.
2. **Verify Secrets Ingestion**:
   - Ensure external secret synchronizers (e.g. AWS Secrets Manager, HashiCorp Vault) have mounted required keys.
3. **Compare Git Commits**:
   - Check the recent CI/CD release to identify if a newly introduced service dependency requires a new configuration key that was omitted in deployment charts.

## Remediation
- Add the missing environment variable or secret key to the deployment environment configuration.
- Trigger a rollout restart of the affected deployment.
- Implement configuration validation with clear defaults or fail-fast schema checks at build time.
