# Data Engineering Technical Test

This is a technical assessment for a Data Engineering position. You will be working with Apache Airflow, PostgreSQL, and Apache Superset to create data pipelines and analytics.

## Prerequisites

Before starting, ensure you have the following installed:

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- At least **4GB of available RAM**
- Available ports: **5432**, **8080**, **8088**

## Getting Started

### 1. Start the Services

Navigate to the project directory and start all services:

```bash
docker compose up -d
```

This will start:
- PostgreSQL database with e-commerce sample data
- Apache Airflow (webserver, scheduler, worker, triggerer)
- Apache Superset for data visualization
- Redis for Airflow's Celery executor

Initial startup takes 2-3 minutes. Monitor progress with:

```bash
docker compose ps
```

Wait until all services show "healthy" status.

### 2. Access the Services

Once all services are healthy, access them at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow** | http://localhost:8080 | Username: `admin`<br>Password: `admin` |
| **Superset** | http://localhost:8088 | Username: `admin`<br>Password: `admin` |
| **PostgreSQL** | `localhost:5432` | User: `datauser`<br>Password: `datapass`<br>Database: `datauser` |

### 3. Verify the Setup

Check that the database is loaded with sample data:

```bash
docker exec postgres-data psql -U datauser -d datauser -c "SELECT COUNT(*) FROM orders;"
```

You should see **50 orders** in the database.

## Database Schema

The PostgreSQL database contains e-commerce data with the following tables:

### `customers`
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR)
- `email` (VARCHAR UNIQUE)
- `created_at` (TIMESTAMP)

**50 customers** in the database.

### `products`
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR)
- `category` (VARCHAR)
- `price` (DECIMAL)
- `stock` (INTEGER)
- `created_at` (TIMESTAMP)

**100 products** across multiple categories (Electronics, Home & Office, Stationery, Accessories).

### `orders`
- `id` (SERIAL PRIMARY KEY)
- `customer_id` (INTEGER, FK to customers)
- `order_date` (TIMESTAMP)
- `total_amount` (DECIMAL)
- `status` (VARCHAR: 'pending', 'processing', 'shipped', 'completed')

**50 orders** spanning January to March 2024.

### `order_items`
- `id` (SERIAL PRIMARY KEY)
- `order_id` (INTEGER, FK to orders)
- `product_id` (INTEGER, FK to products)
- `quantity` (INTEGER)
- `price` (DECIMAL)

Multiple items per order.

### Views

**`order_summary`**: Pre-built view joining orders with customers and aggregating order items.

## Your Task

Create an Apache Airflow DAG that performs the following data transformations. The DAG should run daily and create/update the following tables:

### Task 1: Create `detailed_orders` Table

Create a table that merges `orders` and `order_items` with the following specifications:

**Required Columns:**
- `order_id` - The order ID
- `customer_id` - The customer ID
- `order_date_epoch` - Order date converted to **epoch time** (Unix timestamp)
- `total_amount` - Total order amount
- `status` - Order status
- `items` - An **array/JSON array** of order items, where each item contains:
  - `product_id`
  - `product_name`
  - `quantity`
  - `price`

**Example row structure:**
```
order_id: 1
customer_id: 1
order_date_epoch: 1705747800
total_amount: 1342.97
status: 'completed'
items: [
  {"product_id": 1, "product_name": "Laptop Pro 15", "quantity": 1, "price": 1299.99},
  {"product_id": 2, "product_name": "Wireless Mouse", "quantity": 1, "price": 29.99},
  {"product_id": 3, "product_name": "USB-C Cable", "quantity": 1, "price": 12.99}
]
```

### Task 2: Create `order_tracking` Table

Create a summary table that tracks the number of orders by status.

**Required Columns:**
- `status` - Order status ('pending', 'processing', 'shipped', 'completed')
- `order_count` - Number of orders with this status
- `total_value` - Total dollar value of orders with this status
- `last_updated` - Timestamp when this record was last updated

**Example:**
```
status: 'completed'
order_count: 35
total_value: 15234.50
last_updated: 2024-03-20 10:30:00
```

### Task 3: Create `predictions` Table

Create a table with predictions based on historical data.

**Required Columns:**
- `name` (VARCHAR) - Name/description of the prediction
- `amount` (DECIMAL) - Predicted value

**Required Predictions:**

1. **Total orders for the current month**
   - `name`: 'monthly_orders_prediction'
   - `amount`: Predicted number of orders for the current month based on historical trends

2. **Product category sales predictions**
   - For each product category (Electronics, Home & Office, Stationery, Accessories)
   - `name`: 'category_<category_name>_prediction'
   - `amount`: Predicted number of units that will sell this month for that category

**Example rows:**
```
name: 'monthly_orders_prediction', amount: 45
name: 'category_Electronics_prediction', amount: 120
name: 'category_Home & Office_prediction', amount: 85
name: 'category_Stationery_prediction', amount: 200
name: 'category_Accessories_prediction', amount: 150
```

**Prediction Method:**
You can use any reasonable method for predictions, such as:
- Simple moving average
- Linear trend analysis
- Average growth rate
- Or any other statistical method you prefer

### Task 4: Create Superset Dashboard

Use Apache Superset to create visualizations and a dashboard based on your data.

**Requirements:**

1. **Create at least 3 visualizations** using the tables you created:
   - One visualization from `detailed_orders` (e.g., orders over time, revenue by status)
   - One visualization from `order_tracking` (e.g., pie chart of orders by status)
   - One visualization from `predictions` (e.g., bar chart comparing predictions across categories)

2. **Create a Dashboard** that combines all your visualizations

3. **Take a Screenshot** of your dashboard showing all visualizations

4. **Save the screenshot** in the `screenshots/` directory with the filename: `dashboard.png`

**Tips for Superset:**
- Access Superset at http://localhost:8088
- Go to **SQL Lab** → Select "PostgreSQL Data" database
- Create datasets from your tables: **Data** → **Datasets** → **+ Dataset**
- Create charts: **Charts** → **+ Chart**
- Create dashboard: **Dashboards** → **+ Dashboard**
- Add your charts to the dashboard
- Take a screenshot (use your OS screenshot tool or browser extension)

## Requirements

1. **DAG File**: Create your DAG in the `dags/` directory (e.g., `dags/data_pipeline.py`)

2. **Connection**: Use the pre-configured Airflow connection `postgres_data` to connect to PostgreSQL

3. **Idempotency**: Your DAG should be idempotent - it should be safe to run multiple times without causing errors or duplicate data

4. **Error Handling**: Include appropriate error handling and logging

5. **Task Dependencies**: Structure your tasks with proper dependencies

6. **Documentation**: Include docstrings explaining what each task does

## Validation

After creating your DAG:

1. Enable and trigger the DAG in Airflow UI
2. Verify all tasks complete successfully
3. Check that the three tables were created:

```bash
# Check detailed_orders
docker exec postgres-data psql -U datauser -d datauser -c "SELECT COUNT(*) FROM detailed_orders;"

# Check order_tracking
docker exec postgres-data psql -U datauser -d datauser -c "SELECT * FROM order_tracking;"

# Check predictions
docker exec postgres-data psql -U datauser -d datauser -c "SELECT * FROM predictions;"
```

4. Create your Superset dashboard with visualizations from all three tables
5. Save a screenshot of your dashboard as `screenshots/dashboard.png`

## Managing Services

### View Logs
```bash
docker compose logs -f [service-name]
```

### Stop Services
```bash
docker compose down
```

### Restart with Fresh Data
```bash
docker compose down -v
docker compose up -d
```

### Access PostgreSQL Directly
```bash
docker exec -it postgres-data psql -U datauser -d datauser
```

## Troubleshooting

**Services not starting:**
```bash
docker compose logs
```

**Permission errors:**
```bash
chmod -R 755 dags/
```

**Database connection issues:**
```bash
docker compose logs postgres-data
```

**Airflow DAG not appearing:**
- Wait 1-2 minutes for Airflow to scan the dags folder
- Check for syntax errors: `docker compose logs airflow-scheduler`
- Verify file is in `dags/` directory

## Submission

When complete, ensure:
1. Your DAG file is in the `dags/` directory
2. All tables are created and populated
3. The DAG runs successfully in Airflow
4. Your Superset dashboard screenshot is saved as `screenshots/dashboard.png`
5. Include any additional documentation or notes in comments or a README file

Good luck!
