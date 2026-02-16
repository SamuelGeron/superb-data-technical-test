### TODO:

- [x] Fix airflow db connection with postgres
- [x] Build the `data_pipeline` DAG
  - [x] Setup the runs to capture the missing dates in 2024
  - [x] Enable airflow to trigger dag with config
  - [x] Build the function for the `detailed_orders`
  - [x] Add feature to run Full-refresh
  - [x] Build the function for the `order_tracking`
  - [x] Build the function for the `predictions`
  - [x] Improve predictions
- [x] Create visualizations on Superset
- [ ] Improve the logging and error handling
  - [x] logging
  - [ ] error handling
- [ ] Create tests
- [ ] Improve documentation on what each task does
- [ ] Create step to capture list of items that are on risk based on predicted sales and current stock


## Quick commands

1. Running backfill for a specific date range
```sh
docker exec -it airflow-webserver \
  airflow dags backfill data_pipeline \
  --start-date "2024-3-1" \
  --end-date "2024-3-5"
```
