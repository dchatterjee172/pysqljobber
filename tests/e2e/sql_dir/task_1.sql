-- name: get_1
-- compute_db: db1
-- result_db: db2
select 1::int as result;

-- name: get_a
-- compute_db: db2
-- result_db: db1
select 'a' as result;

-- name: get_true
-- compute_db: db1
-- result_db: db2
select true as result;
