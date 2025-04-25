import pytest
from datamanager import db_manager
from flask import Flask
import os

@pytest.fixture
def app():
    """Create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SQLAlchemy with the app
    db_manager.db.init_app(app)
    
    # Create all tables
    with app.app_context():
        db_manager.db.create_all()
    
    return app

@pytest.fixture
def db_manager_instance(app):
    """Create a SQLiteDataManager instance for testing."""
    manager = db_manager.SQLiteDataManager()
    manager.init_app(app)
    return manager

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        'name': 'Test User',
        'whatsapp_number': '+49123456789',
        'description': 'Test Description',
        'avatar_id': 1
    }

@pytest.fixture
def sample_movie_data():
    """Sample movie data for testing."""
    return {
        'title': 'Test Movie',
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
        assert any(user['name'] == 'Test User' for user in users)
        assert any(user['name'] == 'Another User' for user in users)

def test_add_movie(db_manager_instance, app, sample_movie_data):
    """Test adding a new movie."""
    with app.app_context():
        movie = db_manager_instance.add_movie(sample_movie_data)
        assert movie is not None
        assert movie['title'] == sample_movie_data['title']
        assert movie['description'] == sample_movie_data['description']

def test_get_movie_data(db_manager_instance, app, sample_movie_data):
    """Test retrieving complete movie data."""
    with app.app_context():
        # First add a movie
        movie = db_manager_instance.add_movie(sample_movie_data)
        # Then try to retrieve it
        retrieved_movie = db_manager_instance.get_movie_data(movie['id'])
        assert retrieved_movie is not None
        assert retrieved_movie['title'] == sample_movie_data['title']
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
            'title': 'Updated Movie Title',
            'description': 'Updated Description'
        }
        updated_movie = db_manager_instance.update_movie(movie['id'], updated_data)
        
        assert updated_movie is not None
        assert updated_movie['title'] == 'Updated Movie Title'
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
        category = db_manager.Category(name='Action', img='action.jpg')
        db_manager.db.session.add(category)
        db_manager.db.session.commit()
        
        # Create a movie
        movie = db_manager.Movie(title='Action Movie', description='Action packed!')
        db_manager.db.session.add(movie)
        db_manager.db.session.commit()
        
        # Associate movie with category using the movie_categories table
        db_manager.db.session.execute(
            db_manager.db.text('INSERT INTO movie_categories (movie_id, category_id) VALUES (:movie_id, :category_id)'),
            {'movie_id': movie.id, 'category_id': category.id}
        )
        db_manager.db.session.commit()
        
        # Get movies by category
        movies = db_manager_instance.get_movies_by_category(category.id)
        assert len(movies) == 1
        assert movies[0]['title'] == 'Action Movie'

def test_get_all_categories_with_movies(db_manager_instance, app):
    """Test retrieving all categories with their movies."""
    with app.app_context():
        # Create categories
        action = db_manager.Category(name='Action', img='action.jpg')
        comedy = db_manager.Category(name='Comedy', img='comedy.jpg')
        db_manager.db.session.add_all([action, comedy])
        db_manager.db.session.commit()
        
        # Create movies
        movie1 = db_manager.Movie(title='Action Movie', description='Action packed!')
        movie2 = db_manager.Movie(title='Comedy Movie', description='Very funny!')
        db_manager.db.session.add_all([movie1, movie2])
        db_manager.db.session.commit()
        
        # Associate movies with categories using the movie_categories table
        db_manager.db.session.execute(
            db_manager.db.text('INSERT INTO movie_categories (movie_id, category_id) VALUES (:movie_id1, :category_id1), (:movie_id2, :category_id2)'),
            {
                'movie_id1': movie1.id, 
                'category_id1': action.id,
                'movie_id2': movie2.id, 
                'category_id2': comedy.id
            }
        )
        db_manager.db.session.commit()
        
        # Get all categories with movies
        categories = db_manager_instance.get_all_categories_with_movies()
        assert len(categories) == 2
        assert any(cat['name'] == 'Action' for cat in categories)
        assert any(cat['name'] == 'Comedy' for cat in categories) 