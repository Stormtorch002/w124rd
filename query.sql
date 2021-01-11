CREATE TABLE IF NOT EXISTS npcs ("id" SERIAL PRIMARY KEY, "user_id" BIGINT, "alias" VARCHAR(16), "username" VARCHAR(32), "avatar_url" TEXT);
CREATE TABLE IF NOT EXISTS gvwys ("id" SERIAL PRIMARY KEY, "ch_id" BIGINT, "msg_id" BIGINT, "prize" TEXT, "winners" SMALLINT, "host_id" BIGINT, "role_id" BIGINT, "end" INTEGER, "emoji" VARCHAR(64), "ended" BOOLEAN);
CREATE TABLE IF NOT EXISTS tags ("id" SERIAL PRIMARY KEY, "names" VARCHAR(64) ARRAY, "text" TEXT, "user_id" BIGINT, "uses" INTEGER);
CREATE TABLE IF NOT EXISTS warns ("id" SERIAL PRIMARY KEY, "user_id" BIGINT, "mod_id" BIGINT, "reason" TEXT, "time" INTEGER);
CREATE TABLE IF NOT EXISTS mutes ("id" SERIAL PRIMARY KEY, "user_id" BIGINT UNIQUE, "end" INTEGER);
CREATE TABLE IF NOT EXISTS bans ("id" SERIAL PRIMARY KEY, "user_id" BIGINT UNIQUE, "end" INTEGER);
CREATE TABLE IF NOT EXISTS xp ("id" SERIAL PRIMARY KEY, "user_id" BIGINT UNIQUE, "total_xp" INTEGER, "color" VARCHAR(7), "image" BYTEA);
CREATE TABLE IF NOT EXISTS snipes ("id" SERIAL PRIMARY KEY, "content" TEXT, "user_id" BIGINT, "url" TEXT, "delete" BOOLEAN, "time" INTEGER, "sent" INTEGER);
CREATE TABLE IF NOT EXISTS counts ("id" SERIAL PRIMARY KEY, "user_id" BIGINT, "msg" TEXT, "count" INTEGER, "word" VARCHAR(32), "global" BOOLEAN);