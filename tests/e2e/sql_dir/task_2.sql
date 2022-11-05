-- name: get_2_2
-- compute_db: db2
-- result_db: db1
select 2.2 as result;

-- name: get_multi_row
-- compute_db: db1
-- result_db: db2
select 1::int as result
union all
select 2::int as result
union all
select 3::int as result;

-- name: with_job_args
-- compute_db: db2
-- result_db: db1
select %(arg)s as result;


-- name: sleep_db1
-- compute_db: db1
-- result_db: db2
select 'a' as result
from pg_tables, pg_sleep(1);

-- name: sleep_db2
-- compute_db: db2
-- result_db: db1
select 'a' as result
from pg_tables, pg_sleep(1);
