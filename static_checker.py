import os
import sqlite3

# Connect to the database
db_path = os.path.abspath(os.path.join('data', 'senflix.sqlite'))
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get poster_img from movies_omdb
cursor.execute("SELECT id, imdb_id, poster_img FROM movies_omdb")
movie_posters = cursor.fetchall()

# Check if all files referenced in the DB exist
static_dir = os.path.join('static', 'movies')
existing_files = os.listdir(static_dir)

missing_files = []
for movie_id, imdb_id, poster_img in movie_posters:
    if poster_img and poster_img != 'no-poster.jpg':
        if poster_img not in existing_files:
            missing_files.append((movie_id, imdb_id, poster_img))

print(f"Found {len(movie_posters)} movies in the database.")
print(f"Found {len(existing_files)} files in the static/movies directory.")
print(f"Missing files: {len(missing_files)}")

for movie_id, imdb_id, poster_img in missing_files:
    print(f"Movie ID {movie_id}, IMDB ID {imdb_id}, Poster: {poster_img}")

# Check for image files not referenced in the DB
poster_files = [poster for _, _, poster in movie_posters if poster]
unused_files = [f for f in existing_files if f not in poster_files and f != 'no-poster.jpg']

print(f"\nUnused files: {len(unused_files)}")
for f in unused_files[:10]:  # Limit to 10 to keep output manageable
    print(f)

conn.close() 