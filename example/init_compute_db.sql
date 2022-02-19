create database compute_db;
\c compute_db;
create table entries (
    user_id varchar(64),
    entry_timestamp timestamp not null,
    amount money not null
);
create index user_id_timestamp_entries on entries (user_id, entry_timestamp);

insert into entries(user_id, amount, entry_timestamp)
select
    md5(cast((random() * 200 - 100) as int)::text) as user_id,
    (random() * 200 - 100)::numeric::money as amount,
    now() + (random() * (now()+'90 days' - now())) + '30 days' as entry_timestamp
from generate_series(1, 100000)
order by entry_timestamp;

create database another_compute_db;
\c another_compute_db;
create table entries (
    user_id varchar(64),
    entry_timestamp timestamp not null,
    amount money not null
);
create index user_id_timestamp_entries on entries (user_id, entry_timestamp);

insert into entries(user_id, amount, entry_timestamp)
select
    md5(cast((random() * 200 - 100) as int)::text) as user_id,
    (random() * 200 - 100)::numeric::money as amount,
    now() + (random() * (now()+'90 days' - now())) + '30 days' as entry_timestamp
from generate_series(1, 100000)
order by entry_timestamp;
