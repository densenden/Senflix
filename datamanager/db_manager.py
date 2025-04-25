from flask_sqlalchemy import SQLAlchemy
from .interface import DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, logger
from datetime import datetime
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
import os
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Any
import json
from flask_login import UserMixin

# Initialize SQLAlchemy
db = SQLAlchemy()

class Avatar(db.Model):
    """
    Represents user avatar images in the system.
    
    Attributes:
        id (int): Primary key
        name (str): Avatar name/identifier
        description (str): Avatar description/personality
        profile_image (str): Path to profile image
        hero_image (str): Path to hero/background image
    """
    __tablename__ = 'avatars'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    profile_image = db.Column(db.String(255), nullable=False)
    hero_image = db.Column(db.String(255), nullable=False)
    
    # Relationships
    users = db.relationship('User', back_populates='avatar', lazy='dynamic')
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 100:
            raise ValueError("Name must be between 1 and 100 characters")
        return name
    
    @validates('description')
    def validate_description(self, key, description):
        if not description:
            raise ValueError("Description is required")
        return description
    
    @hybrid_property
    def profile_image_url(self):
        """Returns the full path for the profile image"""
        return f"static/avatars/profile/{self.profile_image}"
    
    @hybrid_property
    def hero_image_url(self):
        """Returns the full path for the hero image"""
        return f"static/avatars/hero/{self.hero_image}"

class User(db.Model, UserMixin):
    """
    Represents a user in the system.
    
    Attributes:
        id (int): Primary key
        name (str): User's name
        whatsapp_number (str): User's WhatsApp contact number
        description (str): User's profile description
        avatar_id (int): Foreign key to Avatar
        created_at (datetime): User creation timestamp
        updated_at (datetime): Last update timestamp
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    whatsapp_number = db.Column(db.String(20), nullable=False, unique=True)
    description = db.Column(db.Text)
    avatar_id = db.Column(db.Integer, db.ForeignKey('avatars.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    avatar = db.relationship('Avatar', back_populates='users')
    favorites = db.relationship('UserFavorite', back_populates='user', cascade='all, delete-orphan')
    
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
            'description': self.description,
            'avatar_id': self.avatar_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    # Flask-Login required methods
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Movie(db.Model):
    """
    Represents a movie in the system.
    
    Attributes:
        id (int): Primary key
        title (str): Movie title
        description (str): Movie description
        created_at (datetime): Movie creation timestamp
        updated_at (datetime): Last update timestamp
    """
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    platforms = db.relationship('StreamingPlatform', secondary='movie_platforms', lazy='dynamic',
                              backref=db.backref('movies', lazy=True))
    categories = db.relationship('Category', secondary='movie_categories', lazy='dynamic',
                               backref=db.backref('movies', lazy=True))
    omdb_data = db.relationship("MovieOMDB", back_populates="movie", uselist=False, cascade='all, delete-orphan')
    favorites = db.relationship('UserFavorite', back_populates='movie', cascade='all, delete-orphan')
    
    @validates('title')
    def validate_title(self, key, title):
        if not title or len(title) > 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return title

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UserFavorite(db.Model):
    """
    Represents a user's favorite movie with additional metadata.
    
    Attributes:
        user_id (int): Foreign key to User
        movie_id (int): Foreign key to Movie
        watched (bool): Whether the user has watched the movie
        comment (str): User's comment about the movie
        rating (float): User's rating of the movie
        watchlist (bool): Whether the movie is on user's watchlist
        created_at (datetime): Favorite creation timestamp
        updated_at (datetime): Last update timestamp
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
        return {
            'user_id': self.user_id,
            'movie_id': self.movie_id,
            'watched': self.watched,
            'comment': self.comment,
            'rating': self.rating,
            'watchlist': self.watchlist,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class StreamingPlatform(db.Model):
    """
    Represents a streaming platform where movies are available.
    
    Attributes:
        id (int): Primary key
        name (str): Name of the streaming platform
        created_at (datetime): Platform creation timestamp
    """
    __tablename__ = 'streaming_platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) > 50:
            raise ValueError("Name must be between 1 and 50 characters")
        return name

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Category(db.Model):
    """
    Represents a movie category/genre.
    
    Attributes:
        id (int): Primary key
        name (str): Name of the category
        img (str): Image filename in static/categories/
        created_at (datetime): Category creation timestamp
    """
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    img = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
        return {
            'id': self.id,
            'name': self.name,
            'img': self.img,
            'img_url': self.img_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MovieOMDB(db.Model):
    """
    Saves OMDB data for a movie from the OMDB API.
    
    Attributes:
        id (int): Foreign key to Movie
        imdb_id (str): IMDb ID
        title (str): Movie title
        year (str): Release year
        rated (str): Movie rating
        released (str): Release date
        runtime (str): Movie runtime
        genre (str): Movie genres
        director (str): Movie director
        writer (str): Movie writers
        actors (str): Movie actors
        plot (str): Movie plot
        language (str): Movie language
        country (str): Movie country
        awards (str): Movie awards
        poster_img (str): Poster image filename
        imdb_rating (str): IMDb rating
        rotten_tomatoes (str): Rotten Tomatoes rating
        metacritic (str): Metacritic rating
        type (str): Content type
        dvd (str): DVD release date
        box_office (str): Box office earnings
        production (str): Production company
        website (str): Movie website
        created_at (datetime): Data creation timestamp
        updated_at (datetime): Last update timestamp
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
    director = db.Column(db.String(100))
    writer = db.Column(db.String(255))
    actors = db.Column(db.String(255))
    plot = db.Column(db.Text)
    language = db.Column(db.String(50))
    country = db.Column(db.String(50))
    awards = db.Column(db.String(255))
    poster_img = db.Column(db.String(255))
    imdb_rating = db.Column(db.String(10))
    rotten_tomatoes = db.Column(db.String(20))
    metacritic = db.Column(db.String(10))
    type = db.Column(db.String(20))
    dvd = db.Column(db.String(20))
    box_office = db.Column(db.String(50))
    production = db.Column(db.String(100))
    website = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    movie = db.relationship('Movie', back_populates='omdb_data')
    
    @hybrid_property
    def poster_url(self):
        """Returns the full path for the poster image"""
        if not self.poster_img:
            return None
        return f"static/movies/{self.poster_img}"

# Junction tables
movie_platforms = db.Table('movie_platforms',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('platform_id', db.Integer, db.ForeignKey('streaming_platforms.id'), primary_key=True)
)

movie_categories = db.Table('movie_categories',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

class SQLiteDataManager(DataManagerInterface):
    """SQLite implementation of the DataManagerInterface."""
    
    def __init__(self):
        self.db = db

    def init_app(self, app):
        """Initialize the database with the Flask app."""
        self.app = app
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///senflix.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.db.init_app(app)
        
        with app.app_context():
            self.db.create_all()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Return list of all users."""
        try:
            users = User.query.all()
            return [user.to_dict() for user in users]
        except SQLAlchemyError as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        """Return movies favorited by the user."""
        try:
            favorites = UserFavorite.query.filter_by(user_id=user_id).all()
            return [favorite.to_dict() for favorite in favorites]
        except SQLAlchemyError as e:
            logger.error(f"Error getting user favorites: {str(e)}")
            return []

    def add_favorite(self, user_id: int, movie_id: int, watched: bool = False, 
                    comment: Optional[str] = None, rating: Optional[int] = None) -> bool:
        """Add a movie to a user's favorites."""
        try:
            favorite = UserFavorite(
                user_id=user_id,
                movie_id=movie_id,
                watched=watched,
                comment=comment,
                rating=rating
            )
            db.session.add(favorite)
            db.session.commit()
            logger.info(f"Added favorite: user_id={user_id}, movie_id={movie_id}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding favorite: {str(e)}")
            return False

    def remove_favorite(self, user_id: int, movie_id: int) -> bool:
        """Remove a movie from user's favorites."""
        try:
            favorite = UserFavorite.query.filter_by(
                user_id=user_id,
                movie_id=movie_id
            ).first()
            if favorite:
                db.session.delete(favorite)
                db.session.commit()
                logger.info(f"Removed favorite: user_id={user_id}, movie_id={movie_id}")
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error removing favorite: {str(e)}")
            return False

    def get_all_movies(self) -> List[Dict[str, Any]]:
        """Return all movies in the database."""
        try:
            movies = Movie.query.all()
            return [movie.to_dict() for movie in movies]
        except SQLAlchemyError as e:
            logger.error(f"Error getting all movies: {str(e)}")
            return []

    def add_movie(self, movie_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new movie to the database."""
        try:
            movie = Movie(**movie_data)
            db.session.add(movie)
            db.session.commit()
            logger.info(f"Added new movie: {movie.title}")
            return movie.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding movie: {str(e)}")
            return None

    def update_movie(self, movie_id: int, movie_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing movie."""
        try:
            movie = Movie.query.get(movie_id)
            if movie:
                for key, value in movie_data.items():
                    setattr(movie, key, value)
                db.session.commit()
                logger.info(f"Updated movie: {movie.title}")
                return movie.to_dict()
            return None
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating movie: {str(e)}")
            return None

    def delete_movie(self, movie_id: int) -> bool:
        """Delete a movie from the database."""
        try:
            movie = Movie.query.get(movie_id)
            if movie:
                db.session.delete(movie)
                db.session.commit()
                logger.info(f"Deleted movie with ID: {movie_id}")
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting movie: {str(e)}")
            return False

    def get_movie_platforms(self, movie_id: int) -> List[Dict[str, Any]]:
        """Return platforms where the movie is available."""
        try:
            movie = Movie.query.get(movie_id)
            if movie:
                return [platform.to_dict() for platform in movie.platforms]
            return []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movie platforms: {str(e)}")
            return []

    def get_movie_categories(self, movie_id: int) -> List[Dict[str, Any]]:
        """Return all category names and images for a given movie."""
        try:
            movie = Movie.query.get(movie_id)
            if movie:
                return [category.to_dict() for category in movie.categories]
            return []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movie categories: {str(e)}")
            return []

    def add_user(self, name: str, whatsapp_number: str, 
                description: Optional[str] = None, 
                avatar_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Create new user with optional description and avatar ID."""
        try:
            user = User(
                name=name,
                whatsapp_number=whatsapp_number,
                description=description,
                avatar_id=avatar_id
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Added new user: {name}")
            return user.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding user: {str(e)}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Return user info for given ID."""
        try:
            user = User.query.get(user_id)
            return user.to_dict() if user else None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def get_movie_data(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Return complete movie data including categories and platforms."""
        try:
            movie = Movie.query.get(movie_id)
            if movie:
                data = movie.to_dict()
                data['categories'] = self.get_movie_categories(movie_id)
                data['platforms'] = self.get_movie_platforms(movie_id)
                return data
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting movie data: {str(e)}")
            return None

    def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Return complete user data including all favorites, comments and watch history."""
        try:
            user = User.query.get(user_id)
            if user:
                data = user.to_dict()
                data['favorites'] = self.get_user_favorites(user_id)
                return data
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting user data: {str(e)}")
            return None

    def get_movies_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """Return all movies in a specific category."""
        try:
            category = Category.query.get(category_id)
            if category:
                return [movie.to_dict() for movie in category.movies]
            return []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movies by category: {str(e)}")
            return []

    def get_all_categories_with_movies(self) -> List[Dict[str, Any]]:
        """Get all categories with their associated movies."""
        try:
            categories = Category.query.all()
            result = []
            for category in categories:
                category_data = category.to_dict()
                category_data['movies'] = self.get_movies_by_category(category.id)
                result.append(category_data)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting categories with movies: {str(e)}")
            return []
