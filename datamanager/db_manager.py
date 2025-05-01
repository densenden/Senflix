from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, logger, Rating, Avatar
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, subqueryload
from typing import Dict, List, Optional, Any
import os
from flask import current_app

class SQLiteDataManager(DataManagerInterface):
    """SQLite implementation of the Data Manager Interface."""
    def __init__(self):
        self.db = db

    def init_app(self, app):
        """Initialize DB with Flask app."""
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            # Default DB path if not configured
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/senflix.sqlite'))
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        # Create tables if they don't exist
        with app.app_context():
            self.db.create_all()

    # --- Private Helper Methods ---

    def _get(self, model, **filters):
        """Helper to get a single record or None."""
        try:
            return model.query.filter_by(**filters).first()
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting {model.__name__} with {filters}: {e}")
            return None

    def _all(self, model, options=None):
        """Helper to get all records, optionally with loading options."""
        try:
            query = model.query
            if options:
                query = query.options(*options)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"DB Error listing {model.__name__}: {e}")
            return []

    def _add_watched_avatars_to_movies(self, movies: List[Dict], limit_avatars=3):
        """Helper to add avatar URLs of users who watched the movies."""
        movie_ids = [m['id'] for m in movies if m.get('id')]
        if not movie_ids:
            return movies # Return original list if no IDs

        try:
            # Efficiently fetch user IDs who watched these movies
            # We use a subquery to get the relevant UserFavorite entries
            # and then join User and Avatar
            watched_entries = db.session.query(
                UserFavorite.movie_id,
                Avatar.image # Select only the image path
            ).join(User, UserFavorite.user_id == User.id)\
             .join(Avatar, User.avatar_id == Avatar.id)\
             .filter(UserFavorite.movie_id.in_(movie_ids))\
             .filter(UserFavorite.watched == True)\
             .order_by(UserFavorite.movie_id)\
             .all()

            # Group avatars by movie_id
            avatars_by_movie = {}
            for movie_id, avatar_image in watched_entries:
                if movie_id not in avatars_by_movie:
                    avatars_by_movie[movie_id] = []
                # Limit the number of avatars per movie
                if len(avatars_by_movie[movie_id]) < limit_avatars:
                    # Construct the full URL path here
                    avatar_url = f"avatars/profile/{avatar_image}" if avatar_image else "avatars/profile/default.png" # Ensure correct default path
                    avatars_by_movie[movie_id].append(avatar_url)

            # Add the avatar list to each movie dictionary
            for movie in movies:
                movie_id = movie.get('id')
                movie['watched_by_avatars'] = avatars_by_movie.get(movie_id, [])

        except SQLAlchemyError as e:
            logger.error(f"DB Error fetching watched avatars: {e}")
            # Continue without avatars if there's an error
            for movie in movies:
                movie['watched_by_avatars'] = [] # Ensure key exists
        except Exception as e: # Catch other potential errors
            logger.error(f"Error processing watched avatars: {e}")
            for movie in movies:
                movie['watched_by_avatars'] = []
                 
        return movies

    # --- User Methods ---

    def get_all_users(self):
        """Get all users as dictionaries."""
        users = self._all(User)
        return [u.to_dict() for u in users]

    def get_user_by_id(self, user_id):
        """Get a single user by ID as dictionary."""
        user = self._get(User, id=user_id)
        return user.to_dict() if user else None

    def add_user(self, name, whatsapp_number, avatar_id=None, description=None):
        """Add a new user."""
        try:
            user = User(
                name=name,
                whatsapp_number=whatsapp_number,
                avatar_id=avatar_id
                # description is part of Avatar, not User model
            )
            db.session.add(user)
            db.session.commit()
            # Return basic user info
            return {
                'id': user.id,
                'name': user.name,
                'whatsapp_number': user.whatsapp_number,
                'avatar_id': user.avatar_id 
            }
        except Exception as e:
            db.session.rollback()
            # Use Flask logger if available
            logger_instance = current_app.logger if current_app else logger
            logger_instance.error(f"Error adding user: {str(e)}")
            return None

    def get_user_data(self, user_id):
        """Get detailed user data including avatar, favorites, ratings."""
        try:
            user = db.session.query(User).options(
                joinedload(User.avatar), # Load avatar details
                joinedload(User.favorites).joinedload(UserFavorite.movie).joinedload(Movie.omdb_data), # Load favorites -> movie -> omdb
                joinedload(User.ratings).joinedload(Rating.movie) # Load ratings -> movie
            ).filter_by(id=user_id).first()
            
            if not user:
                return None
            
            user_dict = user.to_dict()
            # Serialize relationships
            user_dict['favorites'] = [favorite.to_dict() for favorite in user.favorites]
            user_dict['ratings'] = [rating.to_dict() for rating in user.ratings]
            return user_dict
        except Exception as e:
            logger_instance = current_app.logger if current_app else logger
            logger_instance.error(f"Error getting user data for user {user_id}: {str(e)}")
            return None
            
    # --- Movie Methods ---

    def get_all_movies(self):
        """Get all movies with their OMDB data."""
        try:
            # Eager load OMDB data to prevent N+1 queries later
            movies = Movie.query.options(joinedload(Movie.omdb_data)).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting all movies: {e}")
            return []

    def get_movie_data(self, movie_id):
        """Get detailed data for a single movie."""
        try:
            # Eager load necessary relationships
            movie = Movie.query.options(
                joinedload(Movie.omdb_data), 
                subqueryload(Movie.categories),
                subqueryload(Movie.streaming_platforms)
            ).get(movie_id)
            
            return movie.to_dict() if movie else None
        except Exception as e:
            logger.error(f"Error getting movie data for {movie_id}: {e}", exc_info=True) # Add exc_info for traceback
            return None

    def add_movie(self, data: Dict[str, Any]):
        """Add a new movie with optional relations."""
        omdb_data = data.pop('omdb_data', None)
        platform_ids = data.pop('platform_ids', [])
        category_ids = data.pop('category_ids', [])

        try:
            # Create movie object from base data
            movie = Movie(**data)
            
            # Handle OMDB data if provided
            if omdb_data:
                movie.omdb_data = MovieOMDB(**omdb_data)

            # Handle M2M relationships
            if platform_ids:
                platforms = StreamingPlatform.query.filter(StreamingPlatform.id.in_(platform_ids)).all()
                movie.streaming_platforms.extend(platforms)
            if category_ids:
                categories = Category.query.filter(Category.id.in_(category_ids)).all()
                movie.categories.extend(categories)

            db.session.add(movie)
            db.session.commit()
            # Return the full data of the newly added movie
            return self.get_movie_data(movie.id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error adding movie {data.get('name', 'N/A')}: {e}")
            return None
        except Exception as e:
            # Catch other potential errors (e.g., during relationship processing)
            db.session.rollback()
            logger.error(f"Error processing relationships for movie {data.get('name', 'N/A')}: {e}")
            return None

    def update_movie(self, movie_id: int, data: Dict[str, Any]):
        """Update an existing movie."""
        omdb_data = data.pop('omdb_data', None)
        platform_ids = data.pop('platform_ids', None) # Use None to detect if passed
        category_ids = data.pop('category_ids', None)   # Use None to detect if passed

        try:
            # Fetch movie with OMDB data eagerly loaded
            movie = Movie.query.options(joinedload(Movie.omdb_data)).get(movie_id)

            if not movie:
                logger.warning(f"Update failed: Movie with ID {movie_id} not found.")
                return None

            # Update standard movie attributes
            for key, value in data.items():
                if hasattr(movie, key):
                    setattr(movie, key, value)

            # Update or create OMDB data
            if omdb_data:
                if movie.omdb_data:
                    for key, value in omdb_data.items():
                        if hasattr(movie.omdb_data, key):
                            setattr(movie.omdb_data, key, value)
                else:
                    # Create OMDB data if it didn't exist
                    movie.omdb_data = MovieOMDB(**omdb_data, id=movie.id)

            # Update M2M relationships if IDs were provided
            if platform_ids is not None:
                platforms = StreamingPlatform.query.filter(StreamingPlatform.id.in_(platform_ids)).all()
                movie.streaming_platforms = platforms # Replace existing platforms

            if category_ids is not None:
                categories = Category.query.filter(Category.id.in_(category_ids)).all()
                movie.categories = categories # Replace existing categories

            db.session.commit()
            # Return the updated full movie data
            return self.get_movie_data(movie.id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error updating movie {movie_id}: {e}")
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing relationships for update movie {movie_id}: {e}")
            return None

    def delete_movie(self, movie_id: int):
        """Delete a movie by ID."""
        try:
            movie = self._get(Movie, id=movie_id)
            if movie:
                db.session.delete(movie) # Deletes related OMDB data via cascade
                db.session.commit()
                return True
            logger.warning(f"Delete failed: Movie with ID {movie_id} not found.")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error deleting movie {movie_id}: {e}")
            return False

    # --- User Favorite Methods ---

    def upsert_favorite(self, user_id: int, movie_id: int, watched: Optional[bool] = None, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: Optional[bool] = None):
        """Add or update a user's favorite entry for a movie."""
        try:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            if not fav:
                # Create new favorite if it doesn't exist
                fav = UserFavorite(user_id=user_id, movie_id=movie_id)
                # Set initial values if provided during creation
                if watched is not None: fav.watched = watched
                if comment is not None: fav.comment = comment
                if rating is not None: fav.rating = rating
                if watchlist is not None: fav.watchlist = watchlist
                db.session.add(fav)
            else:
                # Update fields only if they are explicitly passed (not None)
                if watched is not None:
                    fav.watched = watched
                if comment is not None: # Allows clearing the comment by passing ""
                    fav.comment = comment
                if rating is not None:
                    # Add validation if needed
                    fav.rating = rating
                if watchlist is not None:
                    fav.watchlist = watchlist
                
            db.session.commit()
            # Return the updated/created favorite object's dict representation
            return fav.to_dict() 
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            return None # Indicate error
        except Exception as e: # Catch other potential errors
            db.session.rollback()
            logger.error(f"Error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            return None # Indicate error
            
    def add_favorite(self, user_id: int, movie_id: int, watched: Optional[bool] = None, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: Optional[bool] = None):
        """Alias for upsert_favorite to fulfill the interface requirement."""
        result = self.upsert_favorite(user_id, movie_id, watched, comment, rating, watchlist)
        return result is not None # Return True on success, False on failure

    def remove_favorite(self, user_id: int, movie_id: int):
        """Remove a movie from a user's favorites."""
        try:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            if fav:
                db.session.delete(fav)
                db.session.commit()
                return True
            logger.warning(f"Remove favorite failed: Entry not found for user {user_id}, movie {movie_id}.")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error removing favorite for user {user_id}, movie {movie_id}: {e}")
            return False

    def get_user_favorites(self, user_id):
        """Get all favorite entries for a user."""
        try:
            # Eager load movie and OMDB data for efficiency
            favorites = UserFavorite.query.options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data)
            ).filter_by(user_id=user_id).all()
            
            result = []
            for favorite in favorites:
                # Start with the movie's dictionary representation
                movie_dict = favorite.movie.to_dict() if favorite.movie else {}
                # Update with favorite-specific details
                movie_dict.update({
                    'user_id': favorite.user_id, # Keep user_id for context
                    'watched': favorite.watched,
                    'comment': favorite.comment,
                    'rating': favorite.rating, # User's rating for this movie
                    'watchlist': favorite.watchlist,
                    # 'created_at': favorite.created_at.isoformat() if favorite.created_at else None # If timestamp existed
                })
                result.append(movie_dict)
            return result
        except Exception as e:
            logger_instance = current_app.logger if current_app else logger
            logger_instance.error(f"Error getting user favorites for user {user_id}: {str(e)}")
            return []

    def get_user_favorite(self, user_id: int, movie_id: int):
         """Get a specific favorite entry for a user and movie.""" 
         fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
         return fav.to_dict() if fav else None
            
    # --- Relationship Getters ---

    def get_movie_platforms(self, movie_id: int):
        """Get streaming platforms for a movie."""
        try:
            movie = Movie.query.options(subqueryload(Movie.streaming_platforms)).get(movie_id)
            return [p.to_dict(include_relationships=False) for p in movie.streaming_platforms] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting platforms for movie {movie_id}: {e}")
            return []

    def get_movie_categories(self, movie_id: int):
        """Get categories for a movie."""
        try:
            movie = Movie.query.options(subqueryload(Movie.categories)).get(movie_id)
            return [c.to_dict(include_relationships=False) for c in movie.categories] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting categories for movie {movie_id}: {e}")
            return []
            
    # --- Category/Platform Specific Getters ---

    def get_movies_by_category(self, category_id: int):
        """Get all movies belonging to a specific category."""
        try:
            # Load category with its movies, and their OMDB data
            category = Category.query.options(
                subqueryload(Category.movies_m2m).joinedload(Movie.omdb_data) # Use the M2M relationship
            ).get(category_id)
            return [m.to_dict() for m in category.movies_m2m] if category else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting movies for category {category_id}: {e}")
            return []

    def get_all_categories(self):
        """Get all categories."""
        # Consider if movie data is needed here; currently fetches only category info
        categories = self._all(Category)
        return [c.to_dict(include_relationships=False) for c in categories] # Avoid loading all movies

    def get_all_platforms(self):
        """Get all streaming platforms."""
        platforms = self._all(StreamingPlatform)
        return [p.to_dict(include_relationships=False) for p in platforms]

    def get_movies_by_platform(self, platform_id: int):
        """Get all movies available on a specific platform."""
        try:
            platform = StreamingPlatform.query.options(
                subqueryload(StreamingPlatform.movies).joinedload(Movie.omdb_data)
            ).get(platform_id)
            return [m.to_dict() for m in platform.movies] if platform else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting movies for platform {platform_id}: {e}")
            return []
            
    def get_all_categories_with_movies(self):
        """Get all categories with their associated movies, loading OMDB data for movies."""
        try:
            # Eager load movies and their OMDB data using joinedload on the m2m relationship
            categories = Category.query.options(
                subqueryload(Category.movies_m2m).joinedload(Movie.omdb_data) 
            ).all()
            return [c.to_dict(include_relationships=True) for c in categories]
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting all categories with movies: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing categories with movies: {e}")
            return []

    # --- List Generation Methods (for main page) ---

    def get_top_rated_movies(self, limit=10, offset=0):
        """Get top rated movies based on average user rating."""
        try:
            # Calculate average rating from UserFavorite table
            movies = Movie.query.options(
                joinedload(Movie.omdb_data),
                # subqueryload(Movie.streaming_platforms), # Load only if needed
                # subqueryload(Movie.categories) # Load only if needed
            ).join(UserFavorite).group_by(Movie.id).order_by(
                db.func.avg(UserFavorite.rating).desc().nullslast()
            ).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting top rated movies: {e}")
            return []

    def get_recent_commented_movies(self, limit=5, offset=0):
        """Get recent comments along with movie and user info."""
        results = []
        try:
            # Eager load related movie (with OMDB) and user (with avatar)
            favorites_query = UserFavorite.query.options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                joinedload(UserFavorite.user).joinedload(User.avatar) # Load user and their avatar
            ).filter(UserFavorite.comment.isnot(None)) # Only entries with comments
            
            # Order by creation date if available
            if hasattr(UserFavorite, 'created_at'):
                favorites_query = favorites_query.order_by(UserFavorite.created_at.desc())
            else:
                 # Fallback: Order by primary key or another field if no timestamp
                 # This might not represent true recency but provides stable order
                 favorites_query = favorites_query.order_by(UserFavorite.user_id.desc(), UserFavorite.movie_id.desc())
                 logger.warning("Cannot order recent comments by date (created_at missing on UserFavorite?). Falling back to ID order.")
            
            favorites = favorites_query.limit(limit).offset(offset).all()

            for fav in favorites:
                if not fav.movie or not fav.user: # Skip if essential data is missing
                    continue 
                    
                movie_dict = fav.movie.to_dict() # Get full movie dict
                user_name = fav.user.name
                # Handle potential missing avatar
                avatar_url = fav.user.avatar.profile_image_url if fav.user.avatar else Avatar().profile_image_url

                results.append({
                    'movie': movie_dict,
                    'comment_text': fav.comment,
                    'comment_user_name': user_name,
                    'comment_user_avatar_url': avatar_url
                })

        except SQLAlchemyError as e:
            logger.error(f"DB Error getting recent commented movies: {e}")
        except Exception as e: # Catch other potential errors during processing
            logger.error(f"Error processing recent commented movies: {e}")
            
        return results
            
    def get_popular_movies(self, limit=10, offset=0):
        """Get popular movies based on number of times they appear in favorites."""
        try:
            # Count favorites per movie
            movies = Movie.query.options(
                joinedload(Movie.omdb_data)
            ).join(UserFavorite).group_by(Movie.id).order_by(
                db.func.count(UserFavorite.movie_id).desc().nullslast()
            ).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting popular movies: {e}")
            return []

    def get_friends_favorites(self, user_id, limit=10, offset=0):
        """Get favorite movies of user's friends (DISABLED)."""
        # This functionality requires the friends relationship which was removed.
        logger.warning(f"Attempted to get friends favorites for user {user_id}, but this feature is disabled.")
        return []
        # Original implementation commented out

    def get_new_releases(self, limit=10, offset=0):
        """Get newest movies based on year."""
        try:
            movies = Movie.query.options(joinedload(Movie.omdb_data)).order_by(
                Movie.year.desc().nullslast(), Movie.id.desc() # Secondary sort for consistency
                ).limit(limit).offset(offset).all()
            return [movie.to_dict() for movie in movies]
        except Exception as e:
            logger.error(f"Error getting new releases: {e}")
            return []
            
    # --- Deprecated/Unused Methods? ---

    # add_rating seems redundant if rating is handled via upsert_favorite
    # def add_rating(self, user_id: int, movie_id: int, rating: float, comment: Optional[str] = None):
    #    ...

    # get_movie_ratings might be redundant if ratings are fetched via get_user_data or get_movie_data?
    # def get_movie_ratings(self, movie_id):
    #    ...
    
    # get_movie_average_rating could be useful but can be calculated from UserFavorite
    # def get_movie_average_rating(self, movie_id):
    #     ...

    # add_favorite is just an alias for upsert_favorite
    # def add_favorite(...)

    # add_category and add_platform might be used by an admin interface or seeding script?
    def add_category(self, category_data):
        """Add a new category."""
        try:
            category = Category(**category_data)
            db.session.add(category)
            db.session.commit()
            return category.to_dict(include_relationships=False)
        except Exception as e:
            db.session.rollback()
            logger_instance = current_app.logger if current_app else logger
            logger_instance.error(f"Error adding category {category_data.get('name')}: {str(e)}")
            return None

    def add_platform(self, platform_data):
        """Add a new streaming platform."""
        try:
            platform = StreamingPlatform(**platform_data)
            db.session.add(platform)
            db.session.commit()
            return platform.to_dict(include_relationships=False)
        except Exception as e:
            db.session.rollback()
            logger_instance = current_app.logger if current_app else logger
            logger_instance.error(f"Error adding platform {platform_data.get('name')}: {str(e)}")
            return None

    # This to_dict method belongs to the Movie class in interface.py, not the manager
    # def to_dict(self):
    #     ...
