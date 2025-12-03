"""
Sample Airflow DAG to demonstrate PostgreSQL connection.

This DAG runs a simple query against the e-commerce database
to verify the connection is working properly.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

# Define the DAG
dag = DAG(
    'sample_postgres_query',
    default_args=default_args,
    description='A simple DAG to query PostgreSQL database',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['example', 'postgres'],
)


def query_customer_stats():
    """
    Query customer statistics from the database using PostgresHook.
    This function demonstrates how to use Python operators with database connections.
    """
    # Create a connection to PostgreSQL using the configured connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_data')

    # Execute query to get customer count
    customer_count = pg_hook.get_first(
        "SELECT COUNT(*) FROM customers"
    )[0]

    # Execute query to get order statistics
    order_stats = pg_hook.get_first("""
        SELECT
            COUNT(*) as total_orders,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders
    """)

    # Print results
    print(f"=== Database Statistics ===")
    print(f"Total Customers: {customer_count}")
    print(f"Total Orders: {order_stats[0]}")
    print(f"Total Revenue: ${order_stats[1]:.2f}")
    print(f"Average Order Value: ${order_stats[2]:.2f}")
    print(f"===========================")

    return {
        'customer_count': customer_count,
        'total_orders': order_stats[0],
        'total_revenue': float(order_stats[1]),
        'avg_order_value': float(order_stats[2])
    }


def query_top_products():
    """
    Query the top 5 products by order frequency.
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_data')

    # Get top products
    top_products = pg_hook.get_records("""
        SELECT
            p.name,
            p.category,
            COUNT(oi.id) as order_count,
            SUM(oi.quantity) as total_sold
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        GROUP BY p.id, p.name, p.category
        ORDER BY order_count DESC
        LIMIT 5
    """)

    print(f"=== Top 5 Products ===")
    for idx, (name, category, order_count, total_sold) in enumerate(top_products, 1):
        print(f"{idx}. {name} ({category}) - {order_count} orders, {total_sold} units sold")
    print(f"======================")

    return top_products


def query_order_status():
    """
    Query order counts by status.
    """
    pg_hook = PostgresHook(postgres_conn_id='postgres_data')

    # Get order status breakdown
    status_counts = pg_hook.get_records("""
        SELECT
            status,
            COUNT(*) as count,
            SUM(total_amount) as total_amount
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """)

    print(f"=== Order Status Breakdown ===")
    for status, count, total_amount in status_counts:
        print(f"{status.upper()}: {count} orders (${total_amount:.2f})")
    print(f"===============================")

    return status_counts


# Task 1: Simple SQL query using PostgresOperator
check_connection = PostgresOperator(
    task_id='check_postgres_connection',
    postgres_conn_id='postgres_data',
    sql='SELECT version();',
    dag=dag,
)

# Task 2: Count customers
count_customers = PostgresOperator(
    task_id='count_customers',
    postgres_conn_id='postgres_data',
    sql='SELECT COUNT(*) as customer_count FROM customers;',
    dag=dag,
)

# Task 3: Get customer statistics using Python
get_customer_stats = PythonOperator(
    task_id='get_customer_stats',
    python_callable=query_customer_stats,
    dag=dag,
)

# Task 4: Get top products
get_top_products = PythonOperator(
    task_id='get_top_products',
    python_callable=query_top_products,
    dag=dag,
)

# Task 5: Get order status breakdown
get_order_status = PythonOperator(
    task_id='get_order_status',
    python_callable=query_order_status,
    dag=dag,
)

# Define task dependencies
check_connection >> count_customers >> [get_customer_stats, get_top_products, get_order_status]
