"""
DAG responsible for the main data pipeline for the fictional e-commerce

The idea behind this DAG is to generate three main tables:
    - detailed_orders: A merge of orders and order items keeping items info as a json column
    - order_tracking: Per status what's the total order count/value and when was the info last updated
    - predictions: Prediction on monhtly sales per category of product

Base tables contains the following indexes:
    - orders: customer_id, order_date(timestamp)
    - order_items: order_id, product_id
    - products: category
    - customers: na
"""
from datetime import date, datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
import logging

# Constants
DAG_INCREMENTAL_LOOKBACK_DAYS = 3
SOURCE_SCHEMA = 'public'
TARGET_SCHEMA = 'analytics'

# Setup logger
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False
    # 'retries': 2,
    # 'retry_delay': timedelta(minutes=5),
}

# Setting up the main configs for the DAG
dag = DAG(
    dag_id='data_pipeline',
    description='Main pipeline for creating the datasets used later in Superset',
    schedule='0 7 * * *', # @daily at 7AM
    catchup=False, # Don't capture missed runs
    is_paused_upon_creation=True, # Make sure to run on deploy
    start_date=datetime(2024, 1, 20),
    # end_date=datetime(2024, 3, 20),
    max_active_runs=1,
    default_args=default_args,
    params={
        "full_refresh": False,
    }, # Enable trigger with config
    tags = ['analytics', 'data_pipeline']
)


def query_setup_schema_and_tables():
    '''
    Creates schema and the required tables for downstream tasks
    '''
    logger.info("Starting with db schema and table definitions:")
    
    # SQL statement
    sql = f"""
        -- Create Schema
        CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA};

        -- Create Tables
        -- Detailed Orders
        CREATE TABLE IF NOT EXISTS {TARGET_SCHEMA}.detailed_orders (
            order_id BIGINT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            order_date_epoch BIGINT NOT NULL,
            total_amount NUMERIC NOT NULL,
            status TEXT NOT NULL,
            items JSONB NOT NULL
        );

        -- Order Tracking
        CREATE TABLE IF NOT EXISTS {TARGET_SCHEMA}.order_tracking (
            status TEXT NOT NULL,
            order_count BIGINT NOT NULL,
            total_value NUMERIC NOT NULL,
            last_updated TIMESTAMP NOT NULL
        );

        -- Predictions
        CREATE TABLE IF NOT EXISTS {TARGET_SCHEMA}.predictions (
            name TEXT NOT NULL,
            amount BIGINT NOT NULL
        );

        -- Create Indexes
        CREATE INDEX IF NOT EXISTS idx_detailed_orders_order_date_epoch ON {TARGET_SCHEMA}.detailed_orders(order_date_epoch);
    """
    
    # Establish Connection and run sql
    pg_hook = PostgresHook(postgres_conn_id='postgres_data')
    pg_hook.run(sql)
    logger.info("Task completed")

    return None


def query_create_detailed_orders(logical_date: date, **context):
    """
    Combines orders and order_items data to serve as a base to downstream tasks
    This table can be created with both full-refresh or incremental load
    """
    # Define function variables
    full_refresh = context["params"].get("full_refresh", False)
    target_table = 'detailed_orders'
    where_clause = ""

    if full_refresh:
        # Drop all records
        logger.info("Performing a full refresh. Truncating the table first.")
        sql_cleanup = f"TRUNCATE TABLE {TARGET_SCHEMA}.{target_table};"
    else:
        # Drop respecting the logical date and the set range
        from_date = logical_date - timedelta(days=DAG_INCREMENTAL_LOOKBACK_DAYS)
        to_date = logical_date
        logger.info(f"Performing an incremental load for the range: {from_date} to {to_date}")

        # Drop data for the range we are running
        sql_cleanup = f"""
            -- Drop date range based on dag logical date
            DELETE FROM {TARGET_SCHEMA}.{target_table}
            WHERE order_date_epoch BETWEEN EXTRACT(EPOCH FROM DATE '{from_date}') AND EXTRACT(EPOCH FROM DATE '{to_date}');
        """

        # Make sure to set the WHERE statement for filtering upstream table
        where_clause = f"WHERE o.order_date BETWEEN DATE '{from_date}' AND DATE '{to_date}'"

    # Statement for inserting the data
    sql_inser_data = f"""    
        -- Insert data
        INSERT INTO {TARGET_SCHEMA}.{target_table} 
        (order_id, customer_id, order_date_epoch, total_amount, status, items)
        SELECT
            o.id AS order_id,
            o.customer_id,
            EXTRACT(EPOCH FROM o.order_date) AS order_date_epoch,
            o.total_amount,
            o.status,   
            jsonb_agg(
                jsonb_build_object(
                    'product_id', oi.product_id,
                    'product_name', p.name,
                    'quantity', oi.quantity,
                    'price', oi.price
                )
            ) AS items
        FROM 
            {SOURCE_SCHEMA}.orders AS o
            LEFT JOIN {SOURCE_SCHEMA}.order_items AS oi
                ON oi.order_id = o.id
            LEFT JOIN {SOURCE_SCHEMA}.products AS p
                ON p.id = oi.product_id
        {where_clause}
        GROUP BY
            1,2,3,4,5
        ORDER BY o.id;
    """

    # Establish Connection and run sql
    pg_hook =  PostgresHook(postgres_conn_id='postgres_data')
    pg_hook.run(sql_cleanup)
    pg_hook.run(sql_inser_data)
    logger.info("Task completed")
    
    return None


def query_create_order_tracking():
    '''
    Create a table with summary on the number of oder per status
    '''
    logger.info("Creating the order tracking table:")

    # Define function variables
    target_table = 'order_tracking'

    # Updates the summary table
    sql = f"""
        -- Drop contents from table
        TRUNCATE TABLE {TARGET_SCHEMA}.{target_table};

        -- Insert up to date data
        INSERT INTO {TARGET_SCHEMA}.{target_table} 
        (status, order_count, total_value, last_updated)
        SELECT
            status,
            COUNT(*) AS order_count,
            SUM(total_amount) AS total_value,
            NOW() AS last_updated
        FROM
            {TARGET_SCHEMA}.detailed_orders
        GROUP BY
            1
    """

    # Establish Connection and run sql
    pg_hook =  PostgresHook(postgres_conn_id='postgres_data')
    pg_hook.run(sql)
    logger.info("Task completed")

    return None


def query_compute_predictions():
    """
    Create a table containing the predictions for both orders and units solde per category
    """
    logger.info("Updating the Predictions:")
    
     # Define function variables
    target_table = 'predictions'
    prediction_for_next_n_days = 30

    # Updates the predictions
    sql = f"""
        -- Drop contents from table
        TRUNCATE TABLE {TARGET_SCHEMA}.{target_table};

        -- Calcualte predictions and insert results to predictions table
        WITH
        base_orders_with_items AS (
            SELECT
                order_id,
                order_date_epoch,
                p.category,
                i.product_id,
                i.quantity
            FROM
                {TARGET_SCHEMA}.detailed_orders
                CROSS JOIN LATERAL jsonb_to_recordset(items) AS i(
                    product_id int,
                    quantity int
                )
                LEFT JOIN {SOURCE_SCHEMA}.products AS p
                  ON i.product_id = p.id
        ),

        -- Get orders per day
        orders_per_day AS (
            SELECT
                order_date_epoch,
                COUNT(DISTINCT order_id) AS order_count
            FROM
                base_orders_with_items
            GROUP BY 1
        ),

        -- Use postgresql built-in function for simple linear regression
        orders_model AS (
            SELECT
                regr_slope(order_count, order_date_epoch) AS slope,
                regr_intercept(order_count, order_date_epoch) AS intercept,
                max(order_date_epoch) AS max_epoch
            FROM
                orders_per_day
        ),
        
        -- Calculate the prediction for the next n days
        orders_prediction AS (
            SELECT
                r.future_date,
                coalesce((om.slope * r.future_date) + om.intercept, 0) AS amount
            FROM
                orders_model as om
                CROSS JOIN generate_series(
                    om.max_epoch + 86400,
                    om.max_epoch + ('{prediction_for_next_n_days}' * 86400),
                    86400
                ) AS r(future_date)
        ),
        
        -- Number of items
        items_per_day AS (
            SELECT
                category,
                order_date_epoch,
                SUM(quantity) as total_items
            FROM
                base_orders_with_items
            GROUP BY 1, 2
        ),

        items_model AS (
            SELECT
                category,
                md.max_epoch,
                regr_slope(total_items, order_date_epoch) AS slope,
                regr_intercept(total_items, order_date_epoch) AS intercept
            FROM
                items_per_day
                CROSS JOIN (
                    SELECT MAX(order_date_epoch) AS max_epoch FROM items_per_day
                ) AS md
            GROUP BY 1, 2
        ),

        items_predictions AS (
            SELECT
                category,
                r.future_date,
                coalesce((im.slope * r.future_date) + im.intercept, 0) AS amount
            FROM
                items_model AS im
                CROSS JOIN generate_series(
                    im.max_epoch + 86400,
                    im.max_epoch + ('{prediction_for_next_n_days}' * 86400),
                    86400
                ) AS r(future_date)
        ),
        
        -- Combine Results by calculting the forecast
        combined_results AS (
            SELECT
                'monthly_orders_prediction' AS name,
                SUM(amount) AS amount
            FROM
                orders_prediction
            GROUP BY 1
            UNION ALL
            SELECT
                'category_' || category || '_prediction' AS name,
                SUM(amount) AS amount
            FROM
                items_predictions
            GROUP BY 1
        ),

        -- Remove negative forecast
        results AS (
            SELECT
                name,
                CASE
                    WHEN amount < 0 THEN 0
                    ELSE amount
                END AS amount
            FROM
                combined_results
        )

        -- Insert Results
        INSERT INTO {TARGET_SCHEMA}.{target_table} 
        (name, amount)
        SELECT name, amount FROM results;
    """

    # Establish Connection and run sql
    pg_hook =  PostgresHook(postgres_conn_id='postgres_data')
    pg_hook.run(sql)
    logger.info("Task completed")

    return None


# Setup start and end tasks
start = EmptyOperator(task_id="start")
end = EmptyOperator(task_id="end")

# Check if the connection was created and working agains db
check_postgres_connection = PostgresOperator(
    task_id='check_postgres_connection',
    postgres_conn_id='postgres_data',
    sql='SELECT version();',
    dag=dag,
)

# Create schema and table if it doesn't exists
create_schema_and_tables = PythonOperator(
    task_id='create_schema_and_tables',
    python_callable=query_setup_schema_and_tables,
    dag=dag
)

# Creates table combining orders and order items
detailed_orders = PythonOperator(
    task_id='detailed_orders',
    python_callable=query_create_detailed_orders,
    dag=dag,
    provide_context=True
)

# Creates a summary table containing the totals
order_tracking = PythonOperator(
    task_id='order_tracking',
    python_callable=query_create_order_tracking,
    dag=dag
)

# Creates a prediction table
predictions = PythonOperator(
    task_id='predictions',
    python_callable=query_compute_predictions,
    dag=dag
)

# Define tasks chain
(
    start
    >> check_postgres_connection
    >> create_schema_and_tables
    >> detailed_orders
)
detailed_orders >> order_tracking
detailed_orders >> predictions
[order_tracking, predictions] >> end
