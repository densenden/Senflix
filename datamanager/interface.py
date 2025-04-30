from abc import ABC, abstractmethod
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
import logging
import re

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

# Association table for User friends (REMOVED as per user request)
# friends_association = db.Table('friends',
#     db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
#     db.Column('friend_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
# )

class Avatar(db.Model):
    """
    Represents a user's avatar.
    """
    __tablename__ = 'avatars'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    image = db.Column(db.String(255))
    description = db.Column(db.Text)
    
    # Relationships
    users = db.relationship('User', back_populates='avatar')
    
    @property
    def profile_image_url(self):
        """Returns the full path for the profile image"""
        if not self.image:
            return 'avatars/default.png'
        return f"avatars/profile/{self.image}"
    
    @property
    def hero_image_url(self):
        """Returns the full path for the hero image"""
        if not self.image:
            return 'avatars/default.png'
        return f"avatars/hero/{self.image}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'description': self.description,
            'profile_image_url': self.profile_image_url,
            'hero_image_url': self.hero_image_url
        }

class User(db.Model):
    """
    Represents a user in the system.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    whatsapp_number = db.Column(db.String(20))
    avatar_id = db.Column(db.Integer, db.ForeignKey('avatars.id'))
    
    # Relationships
    avatar = db.relationship('Avatar', back_populates='users')
    favorites = db.relationship('UserFavorite', back_populates='user', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', back_populates='user', cascade='all, delete-orphan')
    
    # Friends relationship (REMOVED as per user request)
    # friends = db.relationship(
    #     'User', 
    #     secondary=friends_association,
    #     primaryjoin=(id == friends_association.c.user_id),
    #     secondaryjoin=(id == friends_association.c.friend_id),
    #     backref=db.backref('friend_of', lazy='dynamic'),
    #     lazy='dynamic'
    # )
    
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
        return {
            'id': self.id,
            'name': self.name,
            'whatsapp_number': self.whatsapp_number,
            'avatar': self.avatar.to_dict() if self.avatar else None,
            'created_at': None,  # Diese Felder existieren nicht in der Datenbank
            'updated_at': None   # Diese Felder existieren nicht in der Datenbank
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

class Rating(db.Model):
    """
    Represents a movie rating by a user.
    """
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Relationships
    user = db.relationship('User', back_populates='ratings')
    movie = db.relationship('Movie', back_populates='ratings')
    
    @validates('rating')
    def validate_rating(self, key, rating):
        if rating < 0 or rating > 5:
            raise ValueError("Rating must be between 0 and 5")
        return rating
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class Movie(db.Model):
    """
    Represents a movie in the system.
    """
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    director = db.Column(db.Text)
    year = db.Column(db.Integer)
    rating = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    genre = db.Column(db.Text)
    
    # Relationships
    category = db.relationship('Category', back_populates='movies')
    categories = db.relationship('Category', secondary=movie_categories,
                               back_populates='movies')
    streaming_platforms = db.relationship('StreamingPlatform', secondary=movie_platforms,
                                       back_populates='movies')
    omdb_data = db.relationship("MovieOMDB", back_populates="movie", uselist=False, cascade='all, delete-orphan')
    favorites = db.relationship('UserFavorite', back_populates='movie', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', back_populates='movie', cascade='all, delete-orphan')
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Name cannot be empty")
        return name.strip()

    def to_dict(self, include_relationships=True):
        """Convert movie object to dictionary."""
        movie_dict = {
            'id': self.id,
            'name': self.name,
            'director': self.director,
            'year': self.year,
            'rating': self.rating,
            'genre': self.genre
        }
        if include_relationships:
            movie_dict.update({
                'category': self.category.to_dict() if self.category else None,
                'categories': [c.to_dict(include_relationships=False) for c in self.categories],
                'streaming_platforms': [p.to_dict(include_relationships=False) for p in self.streaming_platforms],
                'omdb_data': self.omdb_data.to_dict() if self.omdb_data else None
            })
        return movie_dict

class UserFavorite(db.Model):
    """
    Represents a user's favorite movie.
    """
    __tablename__ = 'user_favorites'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    watched = db.Column(db.Boolean, default=False)
    watchlist = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float)
    comment = db.Column(db.Text)
    # created_at = db.Column(db.DateTime, server_default=db.func.now()) # REMOVED as per user request
    # updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now()) # REMOVED as per user request
    
    # Relationships
    user = db.relationship('User', back_populates='favorites')
    movie = db.relationship('Movie', back_populates='favorites')

    def to_dict(self):
        """Convert favorite object to dictionary."""
        return {
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'watched': self.watched,
            'watchlist': self.watchlist,
            'rating': self.rating,
            'comment': self.comment
            # 'created_at': self.created_at.isoformat() if self.created_at else None, # REMOVED
            # 'updated_at': self.updated_at.isoformat() if self.updated_at else None  # REMOVED
        }

class StreamingPlatform(db.Model):
    """
    Represents a streaming platform.
    """
    __tablename__ = 'streaming_platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    movies = db.relationship('Movie', secondary=movie_platforms,
                           back_populates='streaming_platforms', overlaps="streaming_platforms")
    awards = db.Column(db.String(255))
    poster_img = db.Column(db.String(255))
    imdb_rating = db.Column(db.Float)
    rotten_tomatoes = db.Column(db.String(10))

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Name cannot be empty")
        return name.strip()

    def to_dict(self, include_relationships=True):
        """Convert platform object to dictionary."""
        platform_dict = {
            'id': self.id,
            'name': self.name
        }
        if include_relationships:
            platform_dict['movies'] = [m.to_dict(include_relationships=False) for m in self.movies]
        return platform_dict

    def effective_poster(self):
        """Returns the effective poster image filename or URL"""
        if hasattr(self, 'poster_img') and self.poster_img:
            return self.poster_img
        # if hasattr(self, 'poster_url') and self.poster_url: # REMOVED
        return None

class Category(db.Model):
    """
    Represents a movie category/genre.
    """
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    img = db.Column(db.Text)
    
    # Relationships
    movies = db.relationship('Movie', back_populates='category')
    movies_m2m = db.relationship('Movie', secondary=movie_categories,
                               back_populates='categories')

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Name cannot be empty")
        return name.strip()

    def to_dict(self, include_relationships=True):
        """Convert category object to dictionary."""
        category_dict = {
            'id': self.id,
            'name': self.name,
            'img': self.img
        }
        if include_relationships:
            # Kombiniere beide Beziehungen
            all_movies = list(set(self.movies + self.movies_m2m))
            category_dict['movies'] = [m.to_dict(include_relationships=False) for m in all_movies]
        return category_dict

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

    @property
    def effective_poster(self):
        """Returns the effective poster image filename or URL"""
        if hasattr(self, 'poster_img') and self.poster_img:
            return self.poster_img
        return None

    def to_dict(self):
        """Convert OMDB data object to dictionary."""
        data = {
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
            'poster_img': self.poster_img if hasattr(self, 'poster_img') else None,
            'effective_poster': self.effective_poster
        }
        
        # Füge optionale Felder hinzu, wenn sie existieren
        if hasattr(self, 'imdb_rating'):
            data['imdb_rating'] = self.imdb_rating
        if hasattr(self, 'rotten_tomatoes'):
            data['rotten_tomatoes'] = self.rotten_tomatoes
        if hasattr(self, 'metacritic'):
            data['metacritic'] = self.metacritic
        if hasattr(self, 'type'):
            data['type'] = self.type
        if hasattr(self, 'dvd'):
            data['dvd'] = self.dvd
        if hasattr(self, 'box_office'):
            data['box_office'] = self.box_office
        if hasattr(self, 'production'):
            data['production'] = self.production
        if hasattr(self, 'website'):
            data['website'] = self.website
            
        return data

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