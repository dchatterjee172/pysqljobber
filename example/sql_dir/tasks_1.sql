-- name: get_profit_summary
-- compute_db: db1
-- result_db: db2
SELECT SUM(amount) AS total, entry_timestamp
FROM entries
WHERE user_id = %(user_id)s
GROUP BY entry_timestamp;

-- name: get_profit_entries
-- compute_db: db2
-- result_db: db1
SELECT * FROM entries WHERE user_id = %(user_id)s;
