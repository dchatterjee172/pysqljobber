

-- name: get_profit_entries_by_date
SELECT * FROM entries WHERE user_id = ? AND entry_timestamp > ? and entry_timestamp < ?;
