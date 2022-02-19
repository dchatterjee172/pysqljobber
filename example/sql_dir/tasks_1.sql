-- name: get_profit_summary
SELECT SUM(amount) AS total, entry_timestamp
FROM entries
GROUP BY entry_date WHERE user_id = ?;

-- name: get_profit_entries
-- compute_db: db0
-- result_db: my_res_db
SELECT * FROM entries WHERE user_id = ?;
