BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "avatars" (
	"id"	INTEGER,
	"name"	TEXT,
	"image"	TEXT,
	"description"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "categories" (
	"id"	INTEGER NOT NULL,
	"name"	VARCHAR(50),
	"img"	TEXT,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "movie_categories" (
	"movie_id"	INTEGER NOT NULL,
	"category_id"	INTEGER NOT NULL,
	PRIMARY KEY("movie_id","category_id"),
	FOREIGN KEY("category_id") REFERENCES "categories"("id"),
	FOREIGN KEY("movie_id") REFERENCES "movies"("id")
);
CREATE TABLE IF NOT EXISTS "movie_platforms" (
	"movie_id"	INTEGER NOT NULL,
	"platform_id"	INTEGER NOT NULL,
	PRIMARY KEY("movie_id","platform_id"),
	FOREIGN KEY("movie_id") REFERENCES "movies"("id"),
	FOREIGN KEY("platform_id") REFERENCES "streaming_platforms"("id")
);
CREATE TABLE IF NOT EXISTS "movies" (
	"id"	INTEGER NOT NULL,
	"name"	VARCHAR(100),
	"director"	TEXT,
	"year"	INTEGER,
	"rating"	REAL,
	"category_id"	INTEGER,
	"genre"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("category_id") REFERENCES "categories"("id")
);
CREATE TABLE IF NOT EXISTS "movies_omdb" (
	"id"	INTEGER NOT NULL,
	"imdb_id"	VARCHAR(20) NOT NULL,
	"title"	VARCHAR(255) NOT NULL,
	"year"	VARCHAR(10),
	"rated"	VARCHAR(10),
	"released"	VARCHAR(50),
	"runtime"	VARCHAR(20),
	"genre"	VARCHAR(255),
	"director"	VARCHAR(255),
	"writer"	VARCHAR(255),
	"actors"	VARCHAR(255),
	"plot"	TEXT,
	"language"	VARCHAR(255),
	"country"	VARCHAR(255),
	"awards"	TEXT,
	"poster_img"	VARCHAR(255),
	"imdb_rating"	VARCHAR(10),
	"rotten_tomatoes"	VARCHAR(10),
	"metacritic"	VARCHAR(10),
	"type"	VARCHAR(20),
	"dvd"	VARCHAR(50),
	"box_office"	VARCHAR(50),
	"production"	VARCHAR(255),
	"website"	VARCHAR(255),
	PRIMARY KEY("id"),
	FOREIGN KEY("id") REFERENCES "movies"("id")
);
CREATE TABLE IF NOT EXISTS "streaming_platforms" (
	"id"	INTEGER NOT NULL,
	"name"	VARCHAR(50),
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "user_favorites" (
	"user_id"	INTEGER NOT NULL,
	"movie_id"	INTEGER NOT NULL,
	"watched"	BOOLEAN,
	"comment"	TEXT,
	"rating"	FLOAT,
	"watchlist"	BOOLEAN,
	PRIMARY KEY("user_id","movie_id"),
	FOREIGN KEY("movie_id") REFERENCES "movies"("id"),
	FOREIGN KEY("user_id") REFERENCES "users"("id")
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER NOT NULL,
	"name"	VARCHAR(100),
	"whatsapp_number"	VARCHAR(20),
	"avatar_id"	INTEGER,
	PRIMARY KEY("id"),
	FOREIGN KEY("avatar_id") REFERENCES "avatars"("id")
);
COMMIT;
