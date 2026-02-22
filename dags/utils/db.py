"""
    Helper for centralising the creation of Postgres connection
    and handling SQL runs
"""
import logging
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

def run_sql(
        postgres_conn_id: str, 
        sql: str = ''
    ) -> None:
    """
    Run a SQL query using the specified Postgres connection.
    """
    hook = PostgresHook(postgres_conn_id=postgres_conn_id)
    connection = hook.get_conn()
    try:
        with connection:  # Handles transaction Atomicity with begin/commits and rollbacks automatically
            with connection.cursor() as cursor:
                logging.info(f"Executing the following SQL: \n{sql}")
                cursor.execute(sql)
                logging.info(f"Rows affected: {cursor.rowcount}")
        logging.info("SQL statements executed successfully")
    except Exception:
        logging.exception("SQL statements failed to execute")
        raise
    finally:
        connection.close()

    return None
