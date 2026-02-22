-- Predictions
-- Create table for predictions
CREATE TABLE IF NOT EXISTS {{ target_schema }}.predictions (
    name TEXT NOT NULL,
    amount INTEGER NOT NULL
);

-- Drop contents from table
TRUNCATE TABLE {{ target_schema }}.predictions;

-- Calcualte predictions and insert results to predictions table
WITH
base_orders_with_items AS (
    SELECT
        order_id,
        order_date_epoch,
        i.category,
        i.product_id,
        i.quantity
    FROM
        {{ target_schema }}.detailed_orders
        CROSS JOIN LATERAL jsonb_to_recordset(items) AS i(
            product_id int,
            category text,
            quantity int
        )
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
            om.max_epoch + ({{ predictions_for_next_n_days }} * 86400),
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

-- Calculate the linear regression model for each category
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

-- Calculate the prediction for the next n days for each category
items_predictions AS (
    SELECT
        category,
        r.future_date,
        coalesce((im.slope * r.future_date) + im.intercept, 0) AS amount
    FROM
        items_model AS im
        CROSS JOIN generate_series(
            im.max_epoch + 86400,
            im.max_epoch + ({{ predictions_for_next_n_days }} * 86400),
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
INSERT INTO {{ target_schema }}.predictions 
(name, amount)
SELECT name, amount FROM results;
