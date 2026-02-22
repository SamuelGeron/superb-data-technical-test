-- Order Tracking
-- Create table for order tracking summary
CREATE TABLE IF NOT EXISTS {{ target_schema }}.order_tracking (
    status TEXT NOT NULL,
    order_count BIGINT NOT NULL,
    total_value NUMERIC NOT NULL,
    last_updated TIMESTAMP NOT NULL
);

-- Drop contents from table
TRUNCATE TABLE {{ target_schema }}.order_tracking;

-- Insert up to date data
INSERT INTO {{ target_schema }}.order_tracking 
(status, order_count, total_value, last_updated)
SELECT
    status,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_value,
    NOW() AS last_updated
FROM
    {{ target_schema }}.detailed_orders
GROUP BY 1;
