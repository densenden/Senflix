import sys
import os
import pytest
from datetime import datetime, timezone
from datamanager.db_manager import SQLiteDataManager
from datamanager.interface import User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, db

# Add the main directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

@pytest.fixture
def db_manager(app):
    manager = SQLiteDataManager()
    manager.init_app(app)
    return manager

@pytest.fixture
def test_user(db_manager, app):
    with app.app_context():
        user_data = {
            'username': 'Test User',
            'email': 'test@example.com',
            'password_hash': 'hashed_password'
        }
        return db_manager.add_user(user_data)

@pytest.fixture
def test_movie(db_manager, app):
    with app.app_context():
        movie_data = {
            'name': 'Test Movie',
            'description': 'A test movie',
            'release_year': 2024,
            'duration_minutes': 120
        }
        return db_manager.add_movie(movie_data)

@pytest.fixture
def test_category(db_manager, app):
    with app.app_context():
        category_data = {
            'name': 'Test Category',
            'description': 'A test category'
        }
        return db_manager.add_category(category_data)

@pytest.fixture
def test_platform(db_manager, app):
    with app.app_context():
        platform_data = {
            'name': 'Test Platform',
            'url': 'https://test-platform.com',
            'logo_url': 'https://test-platform.com/logo.png'
        }
        return db_manager.add_platform(platform_data)

@pytest.fixture
def test_favorite(db_manager, app, test_user, test_movie):
    with app.app_context():
        return db_manager.add_favorite(test_user['id'], test_movie['id'])

@pytest.fixture
def test_rating(db_manager, app, test_user, test_movie):
    with app.app_context():
        return db_manager.add_rating(test_user['id'], test_movie['id'], 4.5, "Great movie!")

def test_add_user(db_manager, app):
    with app.app_context():
        user_data = {
            'username': 'New User',
            'email': 'new@example.com',
            'password_hash': 'hashed_password'
        }
        user = db_manager.add_user(user_data)
        assert user is not None
        assert user['username'] == 'New User'
        assert user['email'] == 'new@example.com'
        assert 'id' in user
        assert 'created_at' in user
        assert 'updated_at' in user

def test_get_user_by_id(db_manager, test_user, app):
    with app.app_context():
        user = db_manager.get_user_by_id(test_user["id"])
        assert user is not None
        assert user["username"] == "Test User"
        assert user["email"] == "test@example.com"
        assert "id" in user
        assert "created_at" in user
        assert "updated_at" in user

def test_add_movie(db_manager, app):
    with app.app_context():
        movie_data = {
            "name": "New Movie",
            "description": "A new movie",
            "release_year": 2024,
            "duration_minutes": 120,
            "omdb_data": {
                "imdb_id": "tt7654321",
                "external_poster_url": "http://example.com/new_poster.jpg",
                "plot": "New plot",
                "director": "New Director",
                "actors": "New Actor 1, New Actor 2",
                "imdb_rating": 9.0
            }
        }
        movie = db_manager.add_movie(movie_data)
        assert movie is not None
        assert movie["name"] == "New Movie"
        assert movie["omdb_data"]["imdb_id"] == "tt7654321"

def test_update_movie(db_manager, test_movie, app):
    with app.app_context():
        update_data = {
            "name": "Updated Movie",
            "description": "An updated movie",
            "omdb_data": {
                "plot": "Updated plot",
                "imdb_rating": 9.5
            }
        }
        updated_movie = db_manager.update_movie(test_movie["id"], update_data)
        assert updated_movie is not None
        assert updated_movie["name"] == "Updated Movie"
        assert updated_movie["omdb_data"]["plot"] == "Updated plot"
        assert updated_movie["omdb_data"]["imdb_rating"] == 9.5

def test_add_favorite(db_manager, test_user, test_movie, app):
    with app.app_context():
        success = db_manager.add_favorite(
            test_user["id"],
            test_movie["id"],
            watched=True,
            comment="Great movie!",
            rating=5.0
        )
        assert success is True

def test_get_user_favorites(db_manager, test_user, test_movie, app):
    with app.app_context():
        # Add a favorite
        db_manager.add_favorite(
            test_user["id"],
            test_movie["id"],
            watched=True,
            comment="Great movie!",
            rating=5.0
        )
        
        favorites = db_manager.get_user_favorites(test_user["id"])
        assert len(favorites) == 1
        assert favorites[0]["name"] == "Test Movie"
        assert favorites[0]["watched"] is True
        assert favorites[0]["comment"] == "Great movie!"
        assert favorites[0]["rating"] == 5.0
        assert "created_at" in favorites[0]

def test_get_movie_ratings(db_manager, test_user, test_movie, app):
    with app.app_context():
        # Add a rating
        db_manager.add_rating(
            test_user["id"],
            test_movie["id"],
            rating=4.5,
            comment="Good movie"
        )
        
        ratings = db_manager.get_movie_ratings(test_movie["id"])
        assert len(ratings) == 1
        assert ratings[0]["rating"] == 4.5
        assert ratings[0]["comment"] == "Good movie"
        assert "user" in ratings[0]
        assert "avatar" in ratings[0]["user"]

def test_get_movie_average_rating(db_manager, test_user, test_movie, app):
    with app.app_context():
        # Add multiple ratings
        db_manager.add_rating(test_user["id"], test_movie["id"], rating=4.0)
        
        # Create a second user
        user2_data = {
            'username': 'Test User 2',
            'email': 'test2@example.com',
            'password_hash': 'hashed_password'
        }
        user2 = db_manager.add_user(user2_data)
        db_manager.add_rating(user2["id"], test_movie["id"], rating=5.0)
        
        # Test the average rating
        avg_rating = db_manager.get_movie_average_rating(test_movie["id"])
        assert avg_rating == 4.5  # (4.0 + 5.0) / 2

def test_get_top_rated_movies(db_manager, test_user, test_movie, app):
    with app.app_context():
        # Add a rating
        db_manager.add_rating(test_user["id"], test_movie["id"], rating=5.0)
        
        top_movies = db_manager.get_top_rated_movies(limit=1)
        assert len(top_movies) == 1
        assert top_movies[0]["name"] == "Test Movie"
        assert "omdb_data" in top_movies[0]
        assert "streaming_platforms" in top_movies[0]
        assert "categories" in top_movies[0]

def test_get_recent_commented_movies(db_manager, test_user, test_movie, app):
    with app.app_context():
        # Add a comment
        db_manager.add_favorite(
            test_user["id"],
            test_movie["id"],
            comment="Recent comment"
        )
        
        recent_movies = db_manager.get_recent_commented_movies(limit=1)
        assert len(recent_movies) == 1
        assert recent_movies[0]["name"] == "Test Movie"
        assert "omdb_data" in recent_movies[0]
        assert "streaming_platforms" in recent_movies[0]
        assert "categories" in recent_movies[0]

def test_get_user_data(db_manager, app, test_user):
    with app.app_context():
        user_data = db_manager.get_user_data(test_user['id'])
        assert user_data is not None
        assert user_data['username'] == 'Test User'
        assert user_data['email'] == 'test@example.com'
        assert 'avatar' in user_data
        assert 'created_at' in user_data
        assert 'updated_at' in user_data

def test_get_movies_by_category(db_manager, test_movie, test_category, app):
    with app.app_context():
        # Add the movie to the category
        movie = db.session.get(Movie, test_movie["id"])
        category = db.session.get(Category, test_category["id"])
        movie.categories.append(category)
        db.session.commit()

        # Get the movies for the category
        movies = db_manager.get_movies_by_category(test_category["id"])
        assert len(movies) == 1
        assert movies[0]["id"] == test_movie["id"]

def test_get_movies_by_platform(db_manager, test_movie, test_platform, app):
    with app.app_context():
        # Add the movie to the platform
        movie = db.session.get(Movie, test_movie["id"])
        platform = db.session.get(StreamingPlatform, test_platform["id"])
        movie.streaming_platforms.append(platform)
        db.session.commit()

        # Get the movies for the platform
        movies = db_manager.get_movies_by_platform(test_platform["id"])
        assert len(movies) == 1
        assert movies[0]["id"] == test_movie["id"]

def test_get_all_categories_with_movies(db_manager, test_movie, test_category, app):
    with app.app_context():
        # Add the movie to the category
        movie = db.session.get(Movie, test_movie["id"])
        category = db.session.get(Category, test_category["id"])
        movie.categories.append(category)
        db.session.commit()

        # Get all categories with movies
        categories = db_manager.get_all_categories_with_movies()
        assert len(categories) == 1
        assert categories[0]["id"] == test_category["id"]
        assert len(categories[0]["movies"]) == 1
        assert categories[0]["movies"][0]["id"] == test_movie["id"] 