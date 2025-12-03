#!/bin/bash
# Airflow connection initialization script
# This script ensures the PostgreSQL connection is always available

set -e

echo "Initializing Airflow connections..."

# Wait for Airflow to be ready
airflow db check

# Check if postgres_data connection exists
if airflow connections get postgres_data &>/dev/null; then
    echo "Connection 'postgres_data' already exists"
else
    echo "Creating connection 'postgres_data'..."
    airflow connections add 'postgres_data' \
        --conn-type 'postgres' \
        --conn-login 'datauser' \
        --conn-password 'datapass' \
        --conn-host 'postgres-data' \
        --conn-port '5432' \
        --conn-schema 'datauser'
    echo "Connection 'postgres_data' created successfully"
fi

echo "Connection initialization complete"
