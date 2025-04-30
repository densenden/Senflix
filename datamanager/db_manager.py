from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, logger, Rating
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, subqueryload
from typing import Dict, List, Optional, Any
import os
from flask import current_app

class SQLiteDataManager(DataManagerInterface):
    def __init__(self):
        self.db = db

    def init_app(self, app):
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/senflix.sqlite'))
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        with app.app_context():
            self.db.create_all()

    def _get(self, model, **filters):
        try:
            return model.query.filter_by(**filters).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} with filters {filters}: {e}")
            return None

    def _all(self, model, options=None):
        try:
            query = model.query
            if options:
                query = query.options(*options)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error listing {model.__name__}: {e}")
            return []

    def get_all_users(self):
        users = self._all(User)
        return [u.to_dict() for u in users]

    def get_user_by_id(self, user_id):
        user = self._get(User, id=user_id)
        return user.to_dict() if user else None

    def add_user(self, name, whatsapp_number, avatar_id=None, description=None):
        """
        Add a new user to the database.
        
        Args:
            name (str): Name of the user
            whatsapp_number (str): WhatsApp number of the user
            avatar_id (int, optional): ID of the user's avatar
            description (str, optional): User description
                
        Returns:
            dict: User data if successful, None if failed
        """
        try:
            user = User(
                name=name,
                whatsapp_number=whatsapp_number,
                avatar_id=avatar_id
            )
            db.session.add(user)
            db.session.commit()
            return {
                'id': user.id,
                'name': user.name,
                'whatsapp_number': user.whatsapp_number,
                'avatar_id': user.avatar_id
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding user: {str(e)}")
            return None

    def get_all_movies(self):
        """Get all movies."""
        try:
            # Ensure OMDB data is loaded
            movies = Movie.query.options(joinedload(Movie.omdb_data)).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting all movies: {e}")
            return []

    def get_movie_data(self, movie_id):
        """Get detailed movie data including relationships."""
        try:
            movie = Movie.query.get(movie_id)
            return movie.to_dict() if movie else None
        except Exception as e:
            logger.error(f"Error getting movie data for {movie_id}: {e}")
            return None

    def add_movie(self, data: Dict[str, Any]):
        omdb_data = data.pop('omdb_data', None)
        platform_ids = data.pop('platform_ids', [])
        category_ids = data.pop('category_ids', [])

        try:
            movie = Movie(**data)
            if omdb_data:
                movie.omdb_data = MovieOMDB(**omdb_data)

            if platform_ids:
                platforms = StreamingPlatform.query.filter(StreamingPlatform.id.in_(platform_ids)).all()
                movie.streaming_platforms.extend(platforms)
            if category_ids:
                categories = Category.query.filter(Category.id.in_(category_ids)).all()
                movie.categories.extend(categories)

            db.session.add(movie)
            db.session.commit()
            return self.get_movie_data(movie.id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding movie {data.get('name', 'N/A')}: {e}")
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing relationships for movie {data.get('name', 'N/A')}: {e}")
            return None

    def update_movie(self, movie_id: int, data: Dict[str, Any]):
        omdb_data = data.pop('omdb_data', None)
        platform_ids = data.pop('platform_ids', None)
        category_ids = data.pop('category_ids', None)

        try:
            movie = Movie.query.options(
                joinedload(Movie.omdb_data)
            ).filter_by(id=movie_id).first()

            if not movie:
                return None

            for key, value in data.items():
                if hasattr(movie, key):
                    setattr(movie, key, value)

            if omdb_data:
                if movie.omdb_data:
                    for key, value in omdb_data.items():
                        if hasattr(movie.omdb_data, key):
                            setattr(movie.omdb_data, key, value)
                else:
                    movie.omdb_data = MovieOMDB(**omdb_data, id=movie.id)

            if platform_ids is not None:
                platforms = StreamingPlatform.query.filter(StreamingPlatform.id.in_(platform_ids)).all()
                movie.streaming_platforms = platforms

            if category_ids is not None:
                categories = Category.query.filter(Category.id.in_(category_ids)).all()
                movie.categories = categories

            db.session.commit()
            return self.get_movie_data(movie.id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating movie {movie_id}: {e}")
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing relationships for update movie {movie_id}: {e}")
            return None

    def delete_movie(self, movie_id: int):
        try:
            movie = self._get(Movie, id=movie_id)
            if movie:
                db.session.delete(movie)
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error deleting movie {movie_id}: {e}")
            return False

    def upsert_favorite(self, user_id: int, movie_id: int, watched: bool = False, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: bool = False):
        try:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            if not fav:
                fav = UserFavorite(user_id=user_id, movie_id=movie_id)
                db.session.add(fav)

            fav.watched = watched
            fav.comment = comment
            fav.rating = rating
            fav.watchlist = watchlist

            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            return False

    def remove_favorite(self, user_id: int, movie_id: int):
        try:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            if fav:
                db.session.delete(fav)
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error removing favorite for user {user_id}, movie {movie_id}: {e}")
            return False

    def get_user_favorites(self, user_id):
        """
        Get all favorite movies for a user.
        
        Args:
            user_id (int): The ID of the user
            
        Returns:
            list: List of favorite movie dictionaries
        """
        try:
            favorites = UserFavorite.query.filter_by(user_id=user_id).all()
            result = []
            for favorite in favorites:
                movie_dict = favorite.movie.to_dict()
                movie_dict.update({
                    'watched': favorite.watched,
                    'comment': favorite.comment,
                    'rating': favorite.rating,
                    'watchlist': favorite.watchlist,
                    'created_at': favorite.created_at.isoformat() if favorite.created_at else None
                })
                result.append(movie_dict)
            return result
        except Exception as e:
            current_app.logger.error(f"Error getting user favorites: {str(e)}")
            return []

    def get_movie_platforms(self, movie_id: int):
        try:
            movie = Movie.query.options(
                subqueryload(Movie.streaming_platforms)
            ).filter_by(id=movie_id).first()
            return [p.to_dict() for p in movie.streaming_platforms] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"Error getting platforms for movie {movie_id}: {e}")
            return []

    def get_movie_categories(self, movie_id: int):
        try:
            movie = Movie.query.options(
                subqueryload(Movie.categories)
            ).filter_by(id=movie_id).first()
            return [c.to_dict() for c in movie.categories] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"Error getting categories for movie {movie_id}: {e}")
            return []

    def get_movies_by_category(self, category_id: int):
        try:
            category = Category.query.options(
                subqueryload(Category.movies).joinedload(Movie.omdb_data),
                subqueryload(Category.movies).subqueryload(Movie.streaming_platforms),
                subqueryload(Category.movies).subqueryload(Movie.categories)
            ).filter_by(id=category_id).first()
            return [m.to_dict() for m in category.movies] if category else []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movies for category {category_id}: {e}")
            return []

    def get_all_categories_with_movies(self):
        try:
            categories = Category.query.options(
                subqueryload(Category.movies).joinedload(Movie.omdb_data),
                subqueryload(Category.movies).subqueryload(Movie.streaming_platforms),
                subqueryload(Category.movies).subqueryload(Movie.categories)
            ).all()
            return [c.to_dict() for c in categories]
        except SQLAlchemyError as e:
            logger.error(f"Error getting categories with movies: {e}")
            return []

    def get_all_platforms(self):
        platforms = self._all(StreamingPlatform)
        return [p.to_dict() for p in platforms]

    def get_all_categories(self):
        # Ensure related movies and their OMDB data are loaded
        categories = self._all(Category, options=[
            subqueryload(Category.movies).joinedload(Movie.omdb_data),
            subqueryload(Category.movies_m2m).joinedload(Movie.omdb_data) # Also load for the M2M relationship
        ])
        return [c.to_dict() for c in categories]

    def get_movies_by_platform(self, platform_id: int):
        try:
            platform = StreamingPlatform.query.options(
                subqueryload(StreamingPlatform.movies).joinedload(Movie.omdb_data),
                subqueryload(StreamingPlatform.movies).subqueryload(Movie.streaming_platforms),
                subqueryload(StreamingPlatform.movies).subqueryload(Movie.categories)
            ).filter_by(id=platform_id).first()
            return [m.to_dict() for m in platform.movies] if platform else []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movies for platform {platform_id}: {e}")
            return []

    def get_top_rated_movies(self, limit=10, offset=0):
        """Get top rated movies based on average rating."""
        try:
            # Ensure relationships are loaded to avoid N+1 problems if accessing related data later
            movies = Movie.query.options(
                joinedload(Movie.omdb_data),
                subqueryload(Movie.streaming_platforms),
                subqueryload(Movie.categories)
            ).outerjoin(UserFavorite).group_by(Movie.id).order_by(db.func.avg(UserFavorite.rating).desc().nullslast()).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting top rated movies: {e}")
            return []

    def get_recent_commented_movies(self, limit=5, offset=0):
        """Get movies with recent comments (no specific time order)."""
        try:
            # Cannot order by time as created_at/updated_at are not available
            # Ensure relationships are loaded
            favorites = UserFavorite.query.options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data), # Load movie and its omdb data
                joinedload(UserFavorite.movie).subqueryload(Movie.streaming_platforms),
                joinedload(UserFavorite.movie).subqueryload(Movie.categories)
            ).filter(UserFavorite.comment.isnot(None)).limit(limit).offset(offset).all() # Removed order_by
            # Return the movie data from the favorite object
            # Note: The order is not guaranteed (depends on DB query plan)
            return [fav.movie.to_dict() for fav in favorites]
        except Exception as e:
            logger.error(f"Error getting recent commented movies: {e}")
            return []

    def get_popular_movies(self, limit=10, offset=0):
        """Get popular movies based on number of favorites."""
        try:
            # Count UserFavorite entries per movie_id, not UserFavorite.id
            # Ensure relationships are loaded
            movies = Movie.query.options(
                joinedload(Movie.omdb_data),
                subqueryload(Movie.streaming_platforms),
                subqueryload(Movie.categories)
            ).outerjoin(UserFavorite).group_by(Movie.id).order_by(db.func.count(UserFavorite.movie_id).desc().nullslast()).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting popular movies: {e}")
            return []

    def get_friends_favorites(self, user_id, limit=10, offset=0):
        """Get favorite movies of user's friends (DISABLED - requires friends relationship)."""
        # This functionality is disabled because the friends relationship was removed from the User model
        # as requested, to avoid DB migration.
        logger.warning(f"Attempted to get friends favorites for user {user_id}, but this feature is disabled (requires DB migration for friends table).")
        return []
        # Original code below (commented out):
        # try:
        #     user = User.query.get(user_id)
        #     if not user or not hasattr(user, 'friends'): # Check if friends relationship exists
        #         logger.warning(f"User {user_id} not found or has no friends relationship.")
        #         return []
        #     
        #     # Get friend IDs using the dynamic relationship
        #     friend_ids = [f.id for f in user.friends.all()] # Use .all() for dynamic relationship
        #     if not friend_ids:
        #          logger.info(f"User {user_id} has no friends.")
        #          return []
        #     
        #     # Get friends' favorite movies, ordered by popularity among friends
        #     # Ensure relationships are loaded
        #     friends_favorites = UserFavorite.query.options(
        #         joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
        #         joinedload(UserFavorite.movie).subqueryload(Movie.streaming_platforms),
        #         joinedload(UserFavorite.movie).subqueryload(Movie.categories)
        #     ).filter(UserFavorite.user_id.in_(friend_ids)).group_by(UserFavorite.movie_id).order_by(db.func.count(UserFavorite.user_id).desc()).limit(limit).offset(offset).all()
        #     
        #     # Return the movie data from the favorite object
        #     return [f.movie.to_dict() for f in friends_favorites]
        # except Exception as e:
        #     logger.error(f"Error getting friends favorites: {e}")
        #     return []

    def add_rating(self, user_id: int, movie_id: int, rating: float, comment: Optional[str] = None):
        """
        Add a rating for a movie.
        
        Args:
            user_id (int): The ID of the user
            movie_id (int): The ID of the movie
            rating (float): Rating value between 0 and 5
            comment (str, optional): Comment for the rating. Defaults to None.
            
        Returns:
            dict: Rating data if successful, None if failed
        """
        try:
            r = Rating(
                user_id=user_id,
                movie_id=movie_id,
                rating=rating,
                comment=comment
            )
            db.session.add(r)
            db.session.commit()
            return r.to_dict()
        except Exception as e:
            current_app.logger.error(f"Error adding rating: {str(e)}")
            db.session.rollback()
            return None

    def get_movie_ratings(self, movie_id):
        """
        Get all ratings for a movie.
        
        Args:
            movie_id (int): The ID of the movie
            
        Returns:
            list: List of rating dictionaries
        """
        try:
            ratings = Rating.query.options(
                joinedload(Rating.user)
            ).filter_by(movie_id=movie_id).all()
            return [rating.to_dict() for rating in ratings]
        except Exception as e:
            current_app.logger.error(f"Error getting movie ratings: {str(e)}")
            return []

    def get_movie_average_rating(self, movie_id):
        """
        Get the average rating for a movie.
        
        Args:
            movie_id (int): The ID of the movie
            
        Returns:
            float: Average rating or None if no ratings
        """
        try:
            result = db.session.query(db.func.avg(Rating.rating)).filter(Rating.movie_id == movie_id).scalar()
            return float(result) if result is not None else None
        except Exception as e:
            current_app.logger.error(f"Error getting movie average rating: {str(e)}")
            return None

    def add_favorite(self, user_id: int, movie_id: int, watched: bool = False, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: bool = False):
        return self.upsert_favorite(user_id=user_id, movie_id=movie_id, watched=watched, comment=comment, rating=rating, watchlist=watchlist)

    def get_user_data(self, user_id):
        """
        Get detailed user data including favorites and ratings.
        
        Args:
            user_id (int): The ID of the user
            
        Returns:
            dict: User data dictionary with favorites and ratings
        """
        try:
            user = db.session.query(User).options(
                joinedload(User.avatar),
                joinedload(User.favorites).joinedload(UserFavorite.movie),
                joinedload(User.ratings).joinedload(Rating.movie)
            ).filter_by(id=user_id).first()
            
            if not user:
                return None
            
            user_dict = user.to_dict()
            user_dict['favorites'] = [favorite.to_dict() for favorite in user.favorites]
            user_dict['ratings'] = [rating.to_dict() for rating in user.ratings]
            return user_dict
        except Exception as e:
            current_app.logger.error(f"Error getting user data for user {user_id}: {str(e)}")
            return None

    def add_category(self, category_data):
        """
        Add a new category to the database.
        
        Args:
            category_data (dict): Dictionary containing category data
                - name (str): Name of the category
                - description (str, optional): Description of the category
                
        Returns:
            dict: Category data if successful, None if failed
        """
        try:
            category = Category(
                name=category_data['name'],
                description=category_data.get('description')
            )
            db.session.add(category)
            db.session.commit()
            return {
                'id': category.id,
                'name': category.name,
                'description': category.description
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding category {category_data['name']}: {str(e)}")
            return None

    def add_platform(self, platform_data):
        """
        Add a new streaming platform to the database.
        
        Args:
            platform_data (dict): Dictionary containing platform data
                - name (str): Name of the platform
                - url (str, optional): URL of the platform
                - logo_url (str, optional): URL of the platform's logo
                
        Returns:
            dict: Platform data if successful, None if failed
        """
        try:
            platform = StreamingPlatform(
                name=platform_data['name'],
                url=platform_data.get('url'),
                logo_url=platform_data.get('logo_url')
            )
            db.session.add(platform)
            db.session.commit()
            return {
                'id': platform.id,
                'name': platform.name,
                'url': platform.url,
                'logo_url': platform.logo_url
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding platform {platform_data['name']}: {str(e)}")
            return None

    def get_new_releases(self, limit=10, offset=0):
        """Get most recent movies."""
        try:
            # Ensure OMDB data is loaded
            movies = Movie.query.options(joinedload(Movie.omdb_data)).order_by(Movie.year.desc()).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting new releases: {e}")
            return []
