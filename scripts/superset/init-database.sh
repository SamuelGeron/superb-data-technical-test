#!/bin/bash
# Superset database connection initialization script

set -e

echo "Initializing Superset database connection..."

# Use superset's Python environment with proper Flask app context
export FLASK_APP=superset
python3 <<'PYEOF'
import os
os.environ['FLASK_APP'] = 'superset'

# Import and create app first
from superset.app import create_app
app = create_app()

# Now import models within app context
with app.app_context():
    try:
        # Import within context to avoid errors
        from superset.models.core import Database
        from superset import db

        # Check if connection already exists
        existing = db.session.query(Database).filter_by(
            database_name='PostgreSQL Data'
        ).first()

        if existing:
            print('Database connection "PostgreSQL Data" already exists')
        else:
            # Create new database connection
            database = Database(
                database_name='PostgreSQL Data',
                sqlalchemy_uri='postgresql+psycopg2://datauser:datapass@postgres-data:5432/datauser',
                expose_in_sqllab=True,
                allow_ctas=True,
                allow_cvas=True,
            )

            db.session.add(database)
            db.session.commit()
            print('Database connection "PostgreSQL Data" created successfully')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        db.session.rollback()
        raise

PYEOF

echo "Database connection initialization complete"
