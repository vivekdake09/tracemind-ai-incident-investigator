# Runbook: Database Connection Timeouts

## Description
This runbook covers scenarios where the application is experiencing database connection timeouts, specifically with PostgreSQL.

## Common Symptoms
- Application logs show "FATAL: connection to database failed", "timeout expired", or "psycopg2.OperationalError".
- High latency on API endpoints that rely on DB queries.

## Troubleshooting Steps
1. **Check Database Load**: Check CPU and Memory on the RDS/PostgreSQL instance. If it's maxed out, consider scaling up or finding the query causing the load.
2. **Check Active Connections**: `SELECT sum(numbackends) FROM pg_stat_database;`. If connection limit is reached, check if connection pooling (like pgbouncer) is working correctly.
3. **Check Network/VPC**: Ensure security groups and route tables allow traffic between the app subnets and DB subnets. Did a recent Terraform/Pulumi apply change route tables?
4. **Check DNS**: Is the DB endpoint resolving correctly from the app pods?

## Remediation
- Revert any recent network infrastructure changes.
- Kill long-running blocking queries.
- Increase max connections temporarily if it's a sudden burst, but prefer fixing connection leaks in the application.
