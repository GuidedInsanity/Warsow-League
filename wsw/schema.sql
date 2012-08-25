drop table if exists users;
create table users (
    id integer primary key autoincrement not null,
    username string unique not null,
    email string unique not null,
    password string not null,
    is_admin integer not null default 0,
    is_active integer not null default 1
);

drop table if exists seasons;
create table seasons (
    id integer primary key autoincrement not null,
    signups_open integer not null default 0,
    signup_limit integer not null default 0,
    rules string
);

drop table if exists signups;
create table signups (
    season_id integer not null,
    user_id integer not null,
    division integer default null,
    position integer default null,
    points integer not null default 0,
    wins integer not null default 0,
    draws integer not null default 0,
    losses integer not null default 0,
    FOREIGN KEY(season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY(season_id, user_id)
);

drop table if exists maps;
create table maps (
    id text not null primary key,
    name text not null unique
);

drop table if exists season_maps;
create table season_maps (
    season_id integer not null,
    map_id integer not null,
    FOREIGN KEY(season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    FOREIGN KEY(map_id) REFERENCES maps(id) ON DELETE CASCADE,
    PRIMARY KEY(season_id, map_id)
);

drop table if exists matches;
create table matches (
    id integer not null primary key autoincrement,
    season_id integer not null,
    scheduled integer defeault null,
    locked integer default 0,
    played integer default 0,
    FOREIGN KEY(season_id) REFERENCES seasons(id) ON DELETE CASCADE
);

drop table if exists match_players;
create table match_players (
    match_id integer not null,
    user_id integer not null,
    alpha integer not null,
    schedule_confirmed integer not null default 0,
    result_confirmed integer not null default 0,
    score integer default 0,
    FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY(match_id, user_id)
);

drop table if exists results;
create table results (
    match_id integer not null,
    game_number integer not null,
    map_id string default null,
    alpha_score default null,
    beta_score default null,
    FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
    PRIMARY KEY(map_id, game_number)
);
