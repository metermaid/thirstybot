drop table if exists users;
create table users (
  user_id integer primary key autoincrement,
  username string not null,
  email string not null,
  pw_hash string not null
);

drop table if exists ratings;
create table ratings (
  user_id integer not null,
  drink_id integer not null,
  rating integer not null
);

drop table if exists drinks;
create table drinks (
  drink_id integer primary key autoincrement,
  name string not null,
  description string not null
);

drop table if exists recipes;
create table recipes (
  drink_id integer not null,
  ingredient_id integer not null,
  amount string not null
);
drop table if exists ingredients;
create table ingredients (
  ingredient_id integer primary key autoincrement,
  name string not null
);
drop table if exists cabinets;
create table cabinets (
  user_id integer not null,
  ingredient_id integer not null
);