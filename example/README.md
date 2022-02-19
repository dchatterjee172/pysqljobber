1. Start the services.
    ```shell
    docker-compose up
    ```

    Go to http://localhost:8000 to open the interactive API documentation.

2. Create a job.
    ```shell
    curl -X 'POST' \
      'http://localhost:8000/jobs' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{
      "task_name": "get_profit_summary",
      "job_args": {"user_id": "123"}
    }'
    ```

    This will execute the [task `get_profit_summary`](./sql_dir/tasks_1.sql).

    This is the definition of `get_profit_summary`.

    ```sql
    -- name: get_profit_summary
    -- compute_db: db1
    -- result_db: db2
    SELECT SUM(amount) AS total, entry_timestamp
    FROM entries
    WHERE user_id = %(user_id)s
    GROUP BY entry_timestamp;
    ```

    The query will be executed on `db1` database and the results will be stored in a table on `db2` database.
    You can find the dsn for compute database `db1` and result database `db2` [here](./config_file.toml)

    After you execute the above CURL command, you will get back a `job_id`.

    ```json
    {"job_id":"af38112018ed4e95ad81670a08cb80a4","is_queued":true}
    ```
3. Get job status.
    ```shell
    curl -X 'GET' \
      'http://localhost:8000/jobs?job_id=af38112018ed4e95ad81670a08cb80a4' \
      -H 'accept: application/json'
    ```

    ```json
    {
      "job_id": "af38112018ed4e95ad81670a08cb80a4",
      "task_name": "get_profit_summary",
      "job_status": "COMPLETED",
      "received_at": 1665313680.5144653,
      "queued_at": 1665313680.5152383,
      "dequeued_at": 1665313680.5611215,
      "completed_at": 1665313680.5688772,
      "job_result": "{\"table_name\": \"get_profit_summary_017bdaaffa0f4262afb99210ff60cd0e\"}",
      "error_msg": null
    }
    ```

    Here, the result of the query will be present in the `get_profit_summary_017bdaaffa0f4262afb99210ff60cd0e` table in result database `db2`.
