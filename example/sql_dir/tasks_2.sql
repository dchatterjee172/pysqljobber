-- name: get_profit_entries_by_date
-- compute_db: db1
-- result_db: db2
SELECT * FROM entries
WHERE user_id = %(user_id)s
    AND entry_timestamp >= %(from_entry_timestamp)s
    AND entry_timestamp < %(to_entry_timestamp)s;
