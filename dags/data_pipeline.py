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
import logging
import yaml
from datetime import datetime, timedelta
from utils.db import run_sql
from utils.helpers import get_path_to_file, render_sql_template

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

# Setup logger
logger = logging.getLogger(__name__)
# Import dag configs
config_path = get_path_to_file('config', 'data_pipeline.yml')
dag_config = yaml.safe_load(config_path.read_text())

# Creates DAG using the imported configs
@dag(
    dag_id=dag_config['dag_id'],
    description=dag_config['description'],
    tags=dag_config['tags'],
    start_date=datetime.strptime(dag_config['start_date'], '%Y-%m-%d'),
    schedule=dag_config['schedule'],
    catchup=dag_config['catchup'],
    is_paused_upon_creation=dag_config['is_paused_upon_creation'],
    max_active_runs=dag_config['max_active_runs'],
    default_args=dag_config['default_args'],
    params=dag_config['params'],
)

# Main function for the DAG
def data_pipeline():

    @task
    def check_postgres_connection() -> None:
        """
        Check if the connection with Postgres is working
        """
        logger.info("Checking connection to Postgres")
        run_sql(
            postgres_conn_id=dag_config['vars']['postgres_conn_id'],
            sql="SELECT 1;"
        )
        logger.info("Connection to Postgres is working")

        return None

    @task
    def create_detailed_orders(logical_date = None, full_refresh: bool = False) -> None:
        """
        Combines orders and order_items data to serve as a base to downstream tasks
        This table can be created with both full-refresh or incremental load
        """
        # Get the logical date and the full refresh parameter from the context
        context = get_current_context()
        logical_date = context['logical_date']
        full_refresh = context["params"].get("full_refresh", False)

        # Calculate date range for incremental load and log the parameters
        logger.info("Creating the detailed orders table with parameters:")
        if full_refresh:
            logger.info(" - Full refresh mode")
            from_date = None
            to_date = None
        else:
            # Calculates dates for incremental load
            days = dag_config['vars'].get('incremental_range_in_days')
            if days is None:
                raise ValueError("incremental_range_in_days not defined in DAG config variables")
            from_date = (logical_date - timedelta(days=days)).date()
            to_date = logical_date.date()
            logger.info(" - Incremental load mode:")
            logger.info(f" - Logical Date: {logical_date} - from_date: {from_date} to to_date: {to_date}")
        
        # Render SQL template
        sql_path = get_path_to_file('sql', 'detailed_orders.sql')
        sql_file = sql_path.read_text()
        sql_rendered = render_sql_template(sql_file, {
            'source_schema': dag_config['vars']['source_schema'],
            'target_schema': dag_config['vars']['target_schema'],
            'from_date': from_date,
            'to_date': to_date,
            'full_refresh': full_refresh
        })

        # Run SQL
        run_sql(
            postgres_conn_id=dag_config['vars']['postgres_conn_id'],
            sql=sql_rendered
        )

        return None

    @task
    def create_order_tracking() -> None:
        """
        Create a table with summary on the number of oder per status
        """
        logger.info("Creating the order tracking table:")
        
        # Render SQL template
        sql_path = get_path_to_file('sql', 'order_tracking.sql')
        sql_file = sql_path.read_text()
        sql_rendered = render_sql_template(sql_file, {
            'target_schema': dag_config['vars']['target_schema']
        })

        # Run SQL
        run_sql(
            postgres_conn_id=dag_config['vars']['postgres_conn_id'],
            sql=sql_rendered
        )

        return None

    @task
    def compute_predictions() -> None:
        """
        Create a table with predictions on monthly sales per category of product
        """
        logger.info("Creating the predictions table:")
        
        # Render SQL template
        sql_path = get_path_to_file('sql', 'predictions.sql')
        sql_file = sql_path.read_text()
        sql_rendered = render_sql_template(sql_file, {
            'target_schema': dag_config['vars']['target_schema'],
            'predictions_for_next_n_days': dag_config['vars']['predictions_for_next_n_days']
        })

        # Run SQL
        run_sql(
            postgres_conn_id=dag_config['vars']['postgres_conn_id'],
            sql=sql_rendered
        )

        return None

    # Define tasks
    check_connection = check_postgres_connection()
    detailed_orders = create_detailed_orders()
    order_tracking = create_order_tracking()
    predictions = compute_predictions()

    # Set task dependencies
    (check_connection >> detailed_orders)
    detailed_orders >> order_tracking
    detailed_orders >> predictions

# Create the DAG
dag = data_pipeline()
