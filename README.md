# SenFlix

SenFlix is a web-based movie management application built with Flask and SQLAlchemy. It allows users to browse, rate, and manage movies, as well as create personal profiles and favorite lists. The project is modular and extensible, making it suitable for educational and hobby purposes.

## Table of Contents
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Core Contracts](#core-contracts)
- [Database Manager Methods](#database-manager-methods)
- [Templates/Pages](#templatespages)

## Tech Stack
- **Python 3.8+**
- **Flask** (Web Framework)
- **Flask-SQLAlchemy** (ORM)
- **Jinja2** (Templating)
- **SQLite** (Default Database)
- **HTML/CSS** (Frontend)

## Installation
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd SenFlix
   ```
2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application:**
   ```bash
   flask run
   ```

## Project Structure
```
SenFlix/
  ├── app.py                # Main Flask application
  ├── datamanager/
  │     ├── interface.py    # Data models & contracts
  │     └── db_manager.py   # Database manager implementation
  ├── templates/            # Jinja2 HTML templates
  ├── static/               # Static files (CSS, images)
  └── README.md
```

## Database Schema

The following diagram illustrates the database structure:

![Database Schema](db_schema.png)

## Core Contracts (interface.py)
| Name                | Type        | Description                                                      |
|---------------------|-------------|------------------------------------------------------------------|
| DataManagerInterface| ABC         | Abstract base for data operations (CRUD for users, movies, etc.) |
| db                  | SQLAlchemy  | SQLAlchemy DB instance                                           |
| logger              | Logger      | Logging instance                                                 |
| Avatar              | Model       | User avatar: id, name, description, image                        |
| User                | Model       | User: id, name, whatsapp_number, avatar_id, favorites            |
| Movie               | Model       | Movie: id, name, platforms, categories, favorites                |
| UserFavorite        | Model       | User's favorite: user_id, movie_id, rating, watchlist            |
| StreamingPlatform   | Model       | Streaming platform: id, name                                     |
| Category            | Model       | Category/genre: id, name, img                                    |

## Database Manager Methods (db_manager.py)
| Method                                 | Description                                           |
|----------------------------------------|-------------------------------------------------------|
| __init__                               | Initialize manager with shared DB instance            |
| init_app(app)                          | Setup DB config with Flask app                        |
| _get(model, **filters)                 | Get single object by filter                          |
| _all(model)                            | Get all objects of a model                            |
| get_all_users()                        | Return all users                                      |
| get_user_by_id(user_id)                | Return user data as dict                              |
| add_user(name, whatsapp_number, avatar_id) | Add new user                                    |
| get_all_movies()                       | Return all movies                                     |
| get_movie_data(movie_id)               | Return movie data as dict                             |
| add_movie(data)                        | Add new movie                                         |
| update_movie(mid, data)                | Update movie                                          |
| delete_movie(mid)                      | Delete movie                                          |
| upsert_favorite(user_id, movie_id, ...) | Add or update favorite                              |
| remove_favorite(user_id, movie_id)     | Remove favorite                                       |
| get_user_favorites(user_id)            | Return user's favorites                               |
| get_movie_platforms(movie_id)          | Return movie's platforms                              |
| get_movie_categories(movie_id)         | Return movie's categories                             |
| get_movies_by_category(cid)            | Return movies by category                             |
| get_all_categories_with_movies()       | Return categories with movies                         |
| get_all_platforms()                    | Return all platforms                                  |
| get_all_categories()                   | Return all categories                                 |
| get_movies_by_platform(platform_id)    | Return movies by platform                             |
| get_top_rated_movies(limit=10)         | Return top rated movies                               |
| get_recent_commented_movies(limit=10)  | Return most recently commented movies                 |
| get_popular_movies(limit=10)           | Return most popular movies                            |
| get_friends_favorites(user_id, limit=10)| Return friends' favorites                           |
| add_rating(user_id, movie_id, rating, comment) | Add rating and comment                        |
| get_movie_ratings(movie_id)            | Return all ratings for a movie                        |
| get_movie_average_rating(movie_id)     | Return average rating for a movie                     |
| add_favorite(user_id, movie_id, ...)   | Implement interface method for favorite               |
| get_user_data(user_id)                 | Return all user data including favorites              |

## Templates/Pages (app.py)
| Template/Page         | Description                      |
|----------------------|----------------------------------|
| user_selection.html  | User selection page               |
| movies.html          | Movie overview/listing            |
| movie_detail.html    | Movie detail page                 |
| profile.html         | User profile & stats              |
| search_results.html  | Search results                    |
| users.html           | All users overview                |
| user_movies.html     | Movies for a specific user        |
| add_movie.html       | Add a new movie                   |
| update_movie.html    | Edit a movie                      |
| category_detail.html | Category detail page              |

---

## License
MIT License
