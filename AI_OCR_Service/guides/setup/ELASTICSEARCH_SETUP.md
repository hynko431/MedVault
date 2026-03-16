# Elasticsearch Setup Guide for MedVault

This guide walks you through setting up Elasticsearch 8.x with proper security and a restricted application user.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ with `requests` package installed

## Setup Steps

### Step 1: Start Elasticsearch Cluster

```bash
cd AI_OCR_Service/docker
# Start the 3-node HA production cluster
docker compose -f docker-compose.prod.yml up -d
```

Wait 30-60 seconds for Elasticsearch to fully start.

### Step 2: Get the Elastic Superuser Password

When Elasticsearch starts for the first time, it generates a password for the `elastic` superuser. You have two options:

#### Option A: Use the auto-generated password

```bash
docker logs elasticsearch 2>&1 | grep "generated password"
```

Look for a line like:

```
✅ Password for the elastic user is: XXXXXXXXXXXXXXXXXXXX
```

#### Option B: Reset to a known password

If you want to use your own password, reset it:

```bash
docker exec -it elasticsearch bin/elasticsearch-reset-password -u elastic -i
```

When prompted, enter: `changeme_password123` (or your preferred password)

### Step 3: Create the Application User

Run the setup script to create the `medvault_app` user with restricted permissions:

```bash
cd AI_OCR_Service
python scripts/setup_es_user.py --elastic-pass <elastic_password>
```

Replace `<elastic_password>` with the password from Step 2.

**What this script does:**

1. Creates a custom role `medvault_app_role` with limited cluster and index permissions
2. Creates user `medvault_app` with the custom role
3. Tests the user can connect and perform required operations

### Step 4: Verify the Setup

Run the connection test:

```bash
python tests/test_es_connection.py
```

You should see output like:

```
============================================================
Elasticsearch Connection Check
============================================================

1. Configuration:
   ELASTICSEARCH_ENABLED: True
   ELASTICSEARCH_HOST: http://localhost:9200
   ES_INDEX: prescriptions

2. Client created successfully

3. Testing connection (ping)...
   Ping result: True

4. Getting cluster info...
   Cluster name: docker-cluster
   Version: 8.14.3

5. Checking index 'prescriptions'...
   Index exists: False

You should see output indicating successful connection.

### Step 5: Initialize Production ILM Architecture

To set up the production-grade Index Lifecycle Management (ILM) policies, schema mappings, and routing aliases seamlessly, run the initialization script:

```bash
python scripts/setup_prod_es_ilm.py
```

This ensures zero-downtime scalability and applies the `prescriptions-prod-write` and `prescriptions-prod-read` standard alias patterns required by the backend.

## Configuration Summary

Your `.env` file should have:

```ini
# Enable Elasticsearch
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_HOST="http://localhost:9200"
ES_HOST=http://localhost:9200

# Superuser password (used by docker-compose)
ELASTIC_PASSWORD=changeme_password123

# Application credentials (created by setup script)
ES_USER=medvault_app
ES_PASS=StrongPassword123!
ES_INDEX=prescriptions
ES_VERIFY_CERTS=false
```

## Troubleshooting

### Error: "AuthenticationException(403, 'None')"

This means the `medvault_app` user doesn't exist or the password is incorrect.

**Solution:**

1. Run the setup script again with the correct elastic password:

   ```bash
   python scripts/setup_es_user.py --elastic-pass <correct_password>
   ```

### Error: "Connection refused"

Elasticsearch isn't running or the port isn't exposed.

**Solution:**

```bash
docker-compose ps
docker-compose logs elasticsearch
```

### Error: "Cannot assign requested address"

The `.env` file has `ES_VERIFY_CERTS=true` but you're using HTTP.

**Solution:**
Set `ES_VERIFY_CERTS=false` in your `.env` file.

## Security Notes

- The `medvault_app` user has limited permissions:
  - **Cluster level:** Only `monitor` (read cluster health, stats)
  - **Index level:** `create`, `read`, `write`, `delete`, `create_index`, `view_index_metadata` on `prescriptions` and `prescriptions_*` indices
  
- It **cannot**:
  - Create other users or roles
  - Modify cluster settings
  - Access other indices
  - Delete the cluster

This follows the principle of least privilege for production security.

## Useful Commands

```bash
# Check Elasticsearch is running
curl -u medvault_app:StrongPassword123! http://localhost:9200

# View cluster health
curl -u medvault_app:StrongPassword123! http://localhost:9200/_cluster/health

# List indices and aliases
curl -u medvault_app:StrongPassword123! http://localhost:9200/_cat/indices
curl -u medvault_app:StrongPassword123! http://localhost:9200/_cat/aliases

# Stop Elasticsearch Cluster
docker compose -f docker/docker-compose.prod.yml down

# Start Elasticsearch Cluster
docker compose -f docker/docker-compose.prod.yml up -d

# View logs
docker compose -f docker/docker-compose.prod.yml logs -f es01
```

## Next Steps

After setup is complete:

1. Your application will automatically connect using the read/write query aliases
2. Prescriptions will be indexed automatically to the specific rolling indexes backing the aliases
3. Search functionality will work seamlessly leveraging semantic search mappings in the index templates
