import os
import sqlite3

# Verbindung zur Datenbank herstellen
db_path = os.path.abspath(os.path.join('data', 'senflix.sqlite'))
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Die poster_img aus movies_omdb abrufen
cursor.execute("SELECT id, imdb_id, poster_img FROM movies_omdb")
movie_posters = cursor.fetchall()

# Prüfen, ob alle in der DB referenzierten Dateien existieren
static_dir = os.path.join('static', 'movies')
existing_files = os.listdir(static_dir)

missing_files = []
for movie_id, imdb_id, poster_img in movie_posters:
    if poster_img and poster_img != 'no-poster.jpg':
        if poster_img not in existing_files:
            missing_files.append((movie_id, imdb_id, poster_img))

print(f"Insgesamt {len(movie_posters)} Filme in der Datenbank gefunden.")
print(f"Insgesamt {len(existing_files)} Dateien im static/movies Verzeichnis gefunden.")
print(f"Davon {len(missing_files)} fehlende Dateien:")

for movie_id, imdb_id, poster_img in missing_files:
    print(f"Movie ID {movie_id}, IMDB ID {imdb_id}, Poster: {poster_img}")

# Prüfen, ob es Bilder gibt, auf die keine DB-Einträge verweisen
poster_files = [poster for _, _, poster in movie_posters if poster]
unused_files = [f for f in existing_files if f not in poster_files and f != 'no-poster.jpg']

print(f"\nUngenutzte Dateien: {len(unused_files)}")
for f in unused_files[:10]:  # Begrenzen wir auf 10, um die Ausgabe übersichtlich zu halten
    print(f)

conn.close() 