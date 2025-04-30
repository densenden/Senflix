from abc import ABC, abstractmethod
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()

# Junction tables
movie_platforms = db.Table('movie_platforms',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('platform_id', db.Integer, db.ForeignKey('streaming_platforms.id'), primary_key=True)
)

movie_categories = db.Table('movie_categories',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

class Avatar(db.Model):
    """
    Represents an avatar image for a user.
    """
    __tablename__ = 'avatars'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    
    def to_dict(self):
        """Convert avatar object to dictionary."""
        return {
            'id': self.id,
            'filename': self.filename
        }

class User(db.Model):
    """
    Represents a user in the system.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    whatsapp_number = db.Column(db.String(20), unique=True, nullable=False)
    avatar_id = db.Column(db.Integer, db.ForeignKey('avatars.id'), default=1)
    
    # Relationships
    avatar = db.relationship('Avatar')
    favorites = db.relationship('UserFavorite', back_populates='user')
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 100:
            raise ValueError("Name must be between 1 and 100 characters")
        return name

    @validates('whatsapp_number')
    def validate_whatsapp_number(self, key, number):
        if not number or len(number) > 20:
            raise ValueError("WhatsApp number must be between 1 and 20 characters")
        return number

    def to_dict(self):
        """Convert user object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'whatsapp_number': self.whatsapp_number,
            'avatar_id': self.avatar_id,
            'avatar': self.avatar.to_dict() if self.avatar else None
        }

    # Flask-Login integration for User
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Movie(db.Model):
    """
    Represents a movie in the system.
    """
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    release_year = db.Column(db.Integer)
    duration_minutes = db.Column(db.Integer)
    
    # Relationships
    platforms = db.relationship('StreamingPlatform', secondary='movie_platforms',
                              backref=db.backref('movies', lazy=True))
    categories = db.relationship('Category', secondary='movie_categories',
                               backref=db.backref('movies', lazy=True))
    omdb_data = db.relationship("MovieOMDB", back_populates="movie", uselist=False, cascade='all, delete-orphan')
    favorites = db.relationship('UserFavorite', back_populates='movie', cascade='all, delete-orphan')
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 100:
            raise ValueError("Name must be between 1 and 100 characters")
        return name

    def to_dict(self):
        """Convert movie object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'release_year': self.release_year,
            'duration_minutes': self.duration_minutes,
            'plot': self.omdb_data.plot if hasattr(self, 'omdb_data') and self.omdb_data else None,
            'platforms': [p.to_dict() for p in self.platforms],
            'categories': [c.to_dict() for c in self.categories],
            'omdb_data': self.omdb_data.to_dict() if self.omdb_data else None
        }

class UserFavorite(db.Model):
    """
    Represents a user's favorite movie.
    """
    __tablename__ = 'user_favorites'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    watched = db.Column(db.Boolean, default=False)
    comment = db.Column(db.Text)
    rating = db.Column(db.Float)
    watchlist = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='favorites')
    movie = db.relationship('Movie', back_populates='favorites')
    
    @validates('rating')
    def validate_rating(self, key, rating):
        if rating is not None and (rating < 1 or rating > 10):
            raise ValueError("Rating must be between 1 and 10")
        return rating

    def to_dict(self):
        """Convert favorite object to dictionary."""
        return {
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'watched': self.watched,
            'comment': self.comment,
            'rating': self.rating,
            'watchlist': self.watchlist,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class StreamingPlatform(db.Model):
    """
    Represents a streaming platform where movies are available.
    """
    __tablename__ = 'streaming_platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    url = db.Column(db.String(255))
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 50:
            raise ValueError("Name must be between 1 and 50 characters")
        return name

    def to_dict(self):
        """Convert platform object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url
        }

class Category(db.Model):
    """
    Represents a movie category/genre.
    """
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    img = db.Column(db.String(255))
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 50:
            raise ValueError("Name must be between 1 and 50 characters")
        return name
    
    @hybrid_property
    def img_url(self):
        """Returns the full path for the category image"""
        if not self.img:
            return None
        return f"static/categories/{self.img}"

    def to_dict(self):
        """Convert category object to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'img': self.img,
            'img_url': self.img_url
        }

class MovieOMDB(db.Model):
    """
    Saves OMDB data for a movie from the OMDB API.
    """
    __tablename__ = 'movies_omdb'
    
    id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    imdb_id = db.Column(db.String(20))
    title = db.Column(db.String(255))
    year = db.Column(db.String(10))
    rated = db.Column(db.String(10))
    released = db.Column(db.String(20))
    runtime = db.Column(db.String(20))
    genre = db.Column(db.String(100))
    director = db.Column(db.String(255))
    writer = db.Column(db.String(255))
    actors = db.Column(db.String(255))
    plot = db.Column(db.Text)
    language = db.Column(db.String(50))
    country = db.Column(db.String(50))
    awards = db.Column(db.String(255))
    poster_img = db.Column(db.String(255))
    external_poster_url = db.Column(db.String(255))  # Umbenannt von poster_url
    imdb_rating = db.Column(db.Float)
    rotten_tomatoes = db.Column(db.String(10))
    metacritic = db.Column(db.String(10))
    type = db.Column(db.String(20))
    dvd = db.Column(db.String(20))
    box_office = db.Column(db.String(20))
    production = db.Column(db.String(100))
    website = db.Column(db.String(255))
    
    # Relationships
    movie = db.relationship('Movie', back_populates='omdb_data')
    
    @hybrid_property
    def poster_url(self):
        """Returns the full path for the poster image"""
        if not self.poster_img:
            return self.external_poster_url
        return f"static/movies/{self.poster_img}"

    def to_dict(self):
        """Convert OMDB data object to dictionary."""
        return {
            'id': self.id,
            'imdb_id': self.imdb_id,
            'title': self.title,
            'year': self.year,
            'rated': self.rated,
            'released': self.released,
            'runtime': self.runtime,
            'genre': self.genre,
            'director': self.director,
            'writer': self.writer,
            'actors': self.actors,
            'plot': self.plot,
            'language': self.language,
            'country': self.country,
            'awards': self.awards,
            'poster_img': self.poster_img,
            'poster_url': self.poster_url,
            'external_poster_url': self.external_poster_url,
            'imdb_rating': self.imdb_rating,
            'rotten_tomatoes': self.rotten_tomatoes,
            'metacritic': self.metacritic,
            'type': self.type,
            'dvd': self.dvd,
            'box_office': self.box_office,
            'production': self.production,
            'website': self.website
        }

class DataManagerInterface(ABC):
    """Abstract base class defining the interface for data management operations."""
    
    @abstractmethod
    def init_app(self, app):
        """Initialize the database with the Flask app"""
        pass

    @abstractmethod
    def get_all_users(self):
        """Return list of all users"""
        pass

    @abstractmethod
    def get_user_favorites(self, user_id):
        """Return movies favorited by the user, with watched status, comment and rating"""
        pass

    @abstractmethod
    def add_favorite(self, user_id, movie_id, watched=False, comment=None, rating=None):
        """Add a movie to a user's favorites"""
        pass

    @abstractmethod
    def remove_favorite(self, user_id, movie_id):
        """Remove a movie from user's favorites"""
        pass

    @abstractmethod
    def get_all_movies(self):
        """Return all movies in the database"""
        pass

    @abstractmethod
    def add_movie(self, movie_data):
        """Add a new movie to the database"""
        pass

    @abstractmethod
    def update_movie(self, movie_id, movie_data):
        """Update an existing movie"""
        pass

    @abstractmethod
    def delete_movie(self, movie_id):
        """Delete a movie from the database"""
        pass

    @abstractmethod
    def get_movie_platforms(self, movie_id):
        """Return platforms where the movie is available"""
        pass

    @abstractmethod
    def get_movie_categories(self, movie_id):
        """Return all category names and images for a given movie"""
        pass

    @abstractmethod
    def add_user(self, name, whatsapp_number, description=None, avatar_id=None):
        """Create new user with optional description and avatar ID"""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id):
        """Return user info for given ID"""
        pass

    @abstractmethod
    def get_movie_data(self, movie_id):
        """Return complete movie data including categories and platforms"""
        pass

    @abstractmethod
    def get_user_data(self, user_id):
        """Return complete user data including all favorites, comments and watch history"""
        pass

    @abstractmethod
    def get_movies_by_category(self, category_id):
        """Return all movies in a specific category"""
        pass

    @abstractmethod
    def get_all_categories_with_movies(self):
        """Get all categories with their associated movies"""
        pass