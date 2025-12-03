#!/usr/bin/env python3
"""
Superset database connection initialization script
This script ensures the PostgreSQL database connection is always available
"""

import sys

def init_database_connection():
    """Initialize PostgreSQL database connection in Superset"""
    # Import inside function to avoid app context issues
    from superset import app, db
    from superset.models.core import Database

    with app.app_context():
        try:
            # Check if connection already exists
            existing = db.session.query(Database).filter_by(
                database_name='PostgreSQL Data'
            ).first()

            if existing:
                print('Database connection "PostgreSQL Data" already exists')
                return True

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
            return True

        except Exception as e:
            print(f'Error creating database connection: {e}')
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = init_database_connection()
    sys.exit(0 if success else 1)
