import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datamanager.db_manager import SQLiteDataManager
from datamanager.interface import db, User, Movie, Category, Avatar, UserFavorite
from flask import Flask

@pytest.fixture
def app():
    """Create a Flask app for testing with in-memory SQLite DB."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

@pytest.fixture
def db_manager_instance(app):
    """Create a SQLiteDataManager instance for testing."""
    manager = SQLiteDataManager()
    manager.init_app(app)
    return manager

@pytest.fixture
def sample_user_data():
    """Return unique user data for each test."""
    import time
    return {
        'name': f'Test User {int(time.time()*1000)}',
        'whatsapp_number': f'+49123{int(time.time()*1000)}',
        'description': 'Test Description',
        'avatar_id': 1
    }

@pytest.fixture
def sample_movie_data():
    """Return unique movie data for each test."""
    import time
    return {
        'name': f'Test Movie {int(time.time()*1000)}',
        'description': 'Test Movie Description'
    }

def test_init_app(db_manager_instance, app):
    """Test database initialization."""
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'

def test_add_user(db_manager_instance, app, sample_user_data):
    """Test adding a new user."""
    with app.app_context():
        user = db_manager_instance.add_user(**sample_user_data)
        assert user is not None
        assert user['name'] == sample_user_data['name']
        assert user['whatsapp_number'] == sample_user_data['whatsapp_number']

def test_get_user_by_id(db_manager_instance, app, sample_user_data):
    """Test retrieving a user by ID."""
    with app.app_context():
        # First add a user
        user = db_manager_instance.add_user(**sample_user_data)
        # Then try to retrieve it
        retrieved_user = db_manager_instance.get_user_by_id(user['id'])
        assert retrieved_user is not None
        assert retrieved_user['name'] == sample_user_data['name']

def test_get_all_users(db_manager_instance, app, sample_user_data):
    """Test retrieving all users."""
    with app.app_context():
        # Add multiple users
        db_manager_instance.add_user(**sample_user_data)
        db_manager_instance.add_user(
            name='Another User',
            whatsapp_number='+49987654321',
            description='Another Description',
            avatar_id=1
        )
        
        users = db_manager_instance.get_all_users()
        assert len(users) == 2
        assert any(user['name'] == sample_user_data['name'] for user in users)
        assert any(user['name'] == 'Another User' for user in users)

def test_add_movie(db_manager_instance, app, sample_movie_data):
    """Test adding a new movie."""
    with app.app_context():
        movie = db_manager_instance.add_movie(sample_movie_data)
        assert movie is not None
        assert movie['name'] == sample_movie_data['name']
        assert movie['description'] == sample_movie_data['description']

def test_get_movie_data(db_manager_instance, app, sample_movie_data):
    """Test retrieving complete movie data."""
    with app.app_context():
        # First add a movie
        movie = db_manager_instance.add_movie(sample_movie_data)
        # Then try to retrieve it
        retrieved_movie = db_manager_instance.get_movie_data(movie['id'])
        assert retrieved_movie is not None
        assert retrieved_movie['name'] == sample_movie_data['name']
        assert retrieved_movie['description'] == sample_movie_data['description']

def test_add_favorite(db_manager_instance, app, sample_user_data, sample_movie_data):
    """Test adding a movie to user's favorites."""
    with app.app_context():
        # First create user and movie
        user = db_manager_instance.add_user(**sample_user_data)
        movie = db_manager_instance.add_movie(sample_movie_data)
        
        # Add to favorites
        success = db_manager_instance.add_favorite(
            user_id=user['id'],
            movie_id=movie['id'],
            watched=True,
            comment='Great movie!',
            rating=9
        )
        assert success is True

def test_get_user_favorites(db_manager_instance, app, sample_user_data, sample_movie_data):
    """Test retrieving user's favorites."""
    with app.app_context():
        # Create user and movie
        user = db_manager_instance.add_user(**sample_user_data)
        movie = db_manager_instance.add_movie(sample_movie_data)
        
        # Add to favorites
        db_manager_instance.add_favorite(
            user_id=user['id'],
            movie_id=movie['id'],
            watched=True
        )
        
        # Get favorites
        favorites = db_manager_instance.get_user_favorites(user['id'])
        assert len(favorites) == 1
        assert favorites[0]['movie_id'] == movie['id']
        assert favorites[0]['watched'] is True

def test_remove_favorite(db_manager_instance, app, sample_user_data, sample_movie_data):
    """Test removing a movie from user's favorites."""
    with app.app_context():
        # Create user and movie
        user = db_manager_instance.add_user(**sample_user_data)
        movie = db_manager_instance.add_movie(sample_movie_data)
        
        # Add to favorites
        db_manager_instance.add_favorite(
            user_id=user['id'],
            movie_id=movie['id']
        )
        
        # Remove from favorites
        success = db_manager_instance.remove_favorite(
            user_id=user['id'],
            movie_id=movie['id']
        )
        assert success is True
        
        # Verify it's removed
        favorites = db_manager_instance.get_user_favorites(user['id'])
        assert len(favorites) == 0

def test_update_movie(db_manager_instance, app, sample_movie_data):
    """Test updating a movie."""
    with app.app_context():
        # First add a movie
        movie = db_manager_instance.add_movie(sample_movie_data)
        
        # Update the movie
        updated_data = {
            'name': 'Updated Movie Name',
            'description': 'Updated Description'
        }
        updated_movie = db_manager_instance.update_movie(movie['id'], updated_data)
        
        assert updated_movie is not None
        assert updated_movie['name'] == 'Updated Movie Name'
        assert updated_movie['description'] == 'Updated Description'

def test_delete_movie(db_manager_instance, app, sample_movie_data):
    """Test deleting a movie."""
    with app.app_context():
        # First add a movie
        movie = db_manager_instance.add_movie(sample_movie_data)
        
        # Delete the movie
        success = db_manager_instance.delete_movie(movie['id'])
        assert success is True
        
        # Verify it's deleted
        deleted_movie = db_manager_instance.get_movie_data(movie['id'])
        assert deleted_movie is None

def test_get_movies_by_category(db_manager_instance, app):
    """Test retrieving movies by category."""
    with app.app_context():
        # Create a category
        category = Category(name='Action', img='action.jpg')
        db.session.add(category)
        db.session.commit()
        
        # Create a movie
        movie = Movie(name='Action Movie', description='Action packed!')
        db.session.add(movie)
        db.session.commit()
        
        # Associate movie with category using the movie_categories table
        db.session.execute(
            db.text('INSERT INTO movie_categories (movie_id, category_id) VALUES (:movie_id, :category_id)'),
            {'movie_id': movie.id, 'category_id': category.id}
        )
        db.session.commit()
        
        # Get movies by category
        movies = db_manager_instance.get_movies_by_category(category.id)
        assert len(movies) == 1
        assert movies[0]['name'] == 'Action Movie'

def test_get_all_categories_with_movies(db_manager_instance, app):
    """Test retrieving all categories with their movies."""
    with app.app_context():
        # Create categories
        action = Category(name='Action', img='action.jpg')
        comedy = Category(name='Comedy', img='comedy.jpg')
        db.session.add_all([action, comedy])
        db.session.commit()
        
        # Create movies
        movie1 = Movie(name='Action Movie', description='Action packed!')
        movie2 = Movie(name='Comedy Movie', description='Very funny!')
        db.session.add_all([movie1, movie2])
        db.session.commit()
        
        # Associate movies with categories using the movie_categories table
        db.session.execute(
            db.text('INSERT INTO movie_categories (movie_id, category_id) VALUES (:movie_id1, :category_id1), (:movie_id2, :category_id2)'),
            {
                'movie_id1': movie1.id, 
                'category_id1': action.id,
                'movie_id2': movie2.id, 
                'category_id2': comedy.id
            }
        )
        db.session.commit()
        
        # Get all categories with movies
        categories = db_manager_instance.get_all_categories_with_movies()
        assert len(categories) == 2
        assert any(cat['name'] == 'Action' for cat in categories)
        assert any(cat['name'] == 'Comedy' for cat in categories) 