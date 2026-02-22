-- Detailed Orders
-- Create target schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS {{ target_schema }};

-- All statements for creating the detailed_orders dataset covering both incremental and full refreshes
CREATE TABLE IF NOT EXISTS {{ target_schema }}.detailed_orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    order_date_epoch BIGINT NOT NULL,
    total_amount NUMERIC NOT NULL,
    status TEXT NOT NULL,
    items JSONB NOT NULL
);

-- Create Indexes
CREATE INDEX IF NOT EXISTS idx_detailed_orders_order_date ON {{ target_schema }}.detailed_orders(order_date);

{% if full_refresh %}
-- Remove existing data for a full refresh
TRUNCATE TABLE {{ target_schema }}.detailed_orders;
{% else %}
-- Drop date range based on dag logical date
DELETE FROM {{ target_schema }}.detailed_orders
WHERE order_date BETWEEN '{{ from_date }}' AND '{{ to_date }}';
{% endif %}

-- Insert data into the detailed_orders table
INSERT INTO {{ target_schema }}.detailed_orders
(order_id, customer_id, order_date, order_date_epoch, total_amount, status, items)
SELECT
    o.id AS order_id,
    o.customer_id,
    DATE(o.order_date) AS order_date,
    EXTRACT(EPOCH FROM o.order_date) AS order_date_epoch,
    o.total_amount,
    o.status,   
    jsonb_agg(
        jsonb_build_object(
            'product_id', oi.product_id,
            'category', p.category,
            'product_name', p.name,
            'quantity', oi.quantity,
            'price', oi.price
        )
    ) AS items
FROM 
    {{ source_schema }}.orders AS o
    LEFT JOIN {{ source_schema }}.order_items AS oi
        ON oi.order_id = o.id
    LEFT JOIN {{ source_schema }}.products AS p
        ON p.id = oi.product_id
{%- if not full_refresh %}
WHERE
    o.order_date BETWEEN DATE '{{ from_date }}' AND DATE '{{ to_date }}'
{%- endif %}
GROUP BY
    1, 2, 3, 4, 5, 6
ORDER BY o.id;


