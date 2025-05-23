from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, logger, Rating, Avatar
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, subqueryload
from typing import Dict, List, Optional, Any
import os
from flask import current_app
from flask_login import current_user
from sqlalchemy.sql import func, and_
from sqlalchemy import text

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
        """
        This method is kept for backward compatibility but no longer adds avatar data,
        as avatars have been removed from movie cards.
        """
        # Simply return the movies unmodified
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
            
            result = movie.to_dict() if movie else None
            
            # Check if user is logged in and add user-specific status
            if result and current_user and hasattr(current_user, 'id') and current_user.is_authenticated:
                # Get user favorite data if exists
                user_favorite = UserFavorite.query.get((current_user.id, movie_id))
                if user_favorite:
                    # Add user status to movie data
                    result['user_watched'] = user_favorite.watched
                    result['user_watchlist'] = user_favorite.watchlist
                    result['user_rated'] = user_favorite.rating is not None
                    result['user_favorite'] = user_favorite.favorite
            
            return result
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
            # Return full data after update
            return self.get_movie_data(movie_id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error updating movie {movie_id}: {e}")
            return None
        except Exception as e:
            # Catch other potential errors (e.g., during relationship processing)
            db.session.rollback()
            logger.error(f"General Error updating movie {movie_id}: {e}")
            return None

    def delete_movie(self, movie_id: int):
        """Delete a movie by ID."""
        try:
            movie = self._get(Movie, id=movie_id)
            if movie:
                # Handle related OMDB data if needed (cascade should handle it)
                # Handle UserFavorite manually if cascade is not set or fails
                # UserFavorite.query.filter_by(movie_id=movie_id).delete()
                db.session.delete(movie)
                db.session.commit()
                return True
            logger.warning(f"Delete failed: Movie with ID {movie_id} not found.")
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error deleting movie {movie_id}: {e}")
            return False

    # --- Favorite/Interaction Methods ---

    def upsert_favorite(self, user_id: int, movie_id: int, 
                        watched: Optional[bool] = None, 
                        comment: Optional[str] = None, 
                        rating: Optional[float] = None, 
                        watchlist: Optional[bool] = None,
                        favorite: Optional[bool] = None): # Add favorite parameter
        """Add or update a user's favorite/interaction entry for a movie."""
        try:
            # First check if user and movie exist
            user = User.query.get(user_id)
            if not user:
                logger.error(f"upsert_favorite: User with ID {user_id} does not exist")
                return False
                
            movie = Movie.query.get(movie_id)
            if not movie:
                logger.error(f"upsert_favorite: Movie with ID {movie_id} does not exist")
                return False
                
            fav = UserFavorite.query.get((user_id, movie_id))
            if not fav:
                # Create new entry if it doesn't exist
                fav = UserFavorite(user_id=user_id, movie_id=movie_id)
                db.session.add(fav)
                # Set initial values explicitly, respecting defaults in model if None is passed
                fav.watched = watched if watched is not None else False
                fav.watchlist = watchlist if watchlist is not None else False
                fav.favorite = favorite if favorite is not None else False # Set initial favorite
                fav.rating = rating
                fav.comment = comment
                logger.info(f"New rating created: User {user_id}, Movie {movie_id}, Rating: {rating}")
            else:
                # Update existing entry only if values are provided
                if watched is not None: fav.watched = watched
                if watchlist is not None: fav.watchlist = watchlist
                if favorite is not None: fav.favorite = favorite # Update favorite status
                if rating is not None: fav.rating = rating
                 # Allow clearing comment by passing empty string, but not None
                if comment is not None: fav.comment = comment
                logger.info(f"Existing rating updated: User {user_id}, Movie {movie_id}, Rating: {rating}")
                # Set watched=True if user rates or comments? Common pattern.
                # if rating is not None or (comment is not None and comment.strip() != ''):
                #    fav.watched = True 

            db.session.commit()
            return True # Indicate success
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            # Log additional details for easier debugging
            import traceback
            logger.error(traceback.format_exc())
            return False
        except Exception as e: # Catch potential non-DB errors
            db.session.rollback()
            logger.error(f"General error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            # Log stacktrace for better debugging
            import traceback
            logger.error(traceback.format_exc())
            return False

    def toggle_user_favorite_attribute(self, user_id: int, movie_id: int, attribute: str):
        """Toggles a boolean attribute (watched, watchlist, favorite) for a UserFavorite entry."""
        allowed_attributes = ['watched', 'watchlist', 'favorite']
        if attribute not in allowed_attributes:
            logger.error(f"Invalid attribute '{attribute}' for toggling.")
            return {'error': f"Invalid attribute '{attribute}'"}

        try:
            fav = UserFavorite.query.get((user_id, movie_id))
            current_value = False
            if not fav:
                fav = UserFavorite(user_id=user_id, movie_id=movie_id)
                db.session.add(fav)
                # Set default values for other fields if creating new
                fav.watched = False
                fav.watchlist = False
                fav.favorite = False
                # Set the target attribute to True since it's being toggled from non-existence
                setattr(fav, attribute, True)
                current_value = False # Effective previous value was false
            else:
                current_value = getattr(fav, attribute, False)
                setattr(fav, attribute, not current_value)

            # Optional: Set watched=True if adding to watchlist or favorite?
            # if attribute in ['watchlist', 'favorite'] and getattr(fav, attribute):
            #     fav.watched = True # Or maybe only if rating/comment?

            db.session.commit()
            
            # Return the new state for all attributes
            return {
                'success': True, 
                'new_state': not current_value,
                'user_watched': fav.watched,
                'user_watchlist': fav.watchlist,
                'user_rated': fav.rating is not None
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error toggling '{attribute}' for user {user_id}, movie {movie_id}: {e}")
            return {'error': 'Database error during toggle'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"General error toggling '{attribute}' for user {user_id}, movie {movie_id}: {e}")
            return {'error': 'An error occurred during toggle'}

    def add_favorite(self, user_id: int, movie_id: int, watched: Optional[bool] = None, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: Optional[bool] = None):
        """DEPRECATED: Use upsert_favorite or toggle_user_favorite_attribute instead."""
        # This method is redundant with upsert_favorite. Keep it for compatibility or remove?
        # For now, just call upsert_favorite. Add 'favorite=True' if this specifically means marking as fav.
        logger.warning("Deprecated: add_favorite called, use upsert_favorite or toggle_user_favorite_attribute")
        return self.upsert_favorite(user_id, movie_id, watched=watched, comment=comment, rating=rating, watchlist=watchlist) # Maybe add favorite=True?

    def remove_favorite(self, user_id: int, movie_id: int):
        """Remove a user's favorite/interaction entry for a movie."""
        try:
            fav = UserFavorite.query.get((user_id, movie_id))
            if fav:
                db.session.delete(fav)
                db.session.commit()
                return True
            return False # Return False if not found
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error removing favorite for user {user_id}, movie {movie_id}: {e}")
            return False

    def get_user_favorites(self, user_id):
        """Get all favorite/interaction entries for a user."""
        # This is often handled by get_user_data which eager loads. 
        # If needed standalone:
        try:
            favs = UserFavorite.query.filter_by(user_id=user_id).options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data) # Load movie+omdb
            ).all()
            return [f.to_dict() for f in favs]
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting favorites for user {user_id}: {e}")
            return []

    def get_user_favorite(self, user_id: int, movie_id: int):
        """Get a specific favorite/interaction entry."""
        try:
            logger.info(f"=================== GET_USER_FAVORITE DEBUG ===================")
            logger.info(f"BEGIN get_user_favorite for user_id={user_id}, movie_id={movie_id}")
            
            # Direct SQL query for debugging
            from sqlalchemy import text
            logger.info(f"Executing direct SQL query to find user favorite")
            
            result = db.session.execute(
                text("SELECT * FROM user_favorites WHERE user_id = :user_id AND movie_id = :movie_id"),
                {"user_id": user_id, "movie_id": movie_id}
            ).fetchone()
            
            if result:
                # Convert SQL result to dict for debugging
                result_dict = dict(result)
                logger.info(f"DIRECT SQL QUERY - Found result: {result_dict}")
                logger.info(f"DIRECT SQL QUERY - Rating: {result_dict.get('rating')}, Type: {type(result_dict.get('rating'))}")
                logger.info(f"DIRECT SQL QUERY - Comment: '{result_dict.get('comment')}', Type: {type(result_dict.get('comment'))}")
            else:
                logger.info(f"DIRECT SQL QUERY - No result found")
            
            # Regular ORM query
            logger.info(f"Executing ORM query UserFavorite.query.get(({user_id}, {movie_id}))")
            fav = UserFavorite.query.get((user_id, movie_id))
            
            if fav:
                logger.info(f"ORM QUERY - Found UserFavorite")
                logger.info(f"ORM QUERY - Rating: {fav.rating}, Type: {type(fav.rating)}")
                logger.info(f"ORM QUERY - Comment: '{fav.comment}', Type: {type(fav.comment)}")
                logger.info(f"ORM QUERY - Watched: {fav.watched}, Watchlist: {fav.watchlist}, Favorite: {fav.favorite}")
                
                result = fav.to_dict()
                logger.info(f"RESULT from to_dict(): {result}")
                logger.info(f"RESULT Rating: {result.get('rating')}, Type: {type(result.get('rating'))}")
                logger.info(f"RESULT Comment: '{result.get('comment')}', Type: {type(result.get('comment'))}")
                logger.info(f"=================== END GET_USER_FAVORITE DEBUG ===================")
                return result
            else:
                logger.info(f"ORM QUERY - No UserFavorite found")
                logger.info(f"=================== END GET_USER_FAVORITE DEBUG ===================")
                return None
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting favorite for user {user_id}, movie {movie_id}: {e}")
            logger.error(f"=================== END GET_USER_FAVORITE DEBUG ===================")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_favorite: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error(f"=================== END GET_USER_FAVORITE DEBUG ===================")
            return None

    # --- Query Methods ---

    def get_movie_platforms(self, movie_id: int):
        """Get streaming platforms for a movie."""
        try:
            movie = Movie.query.options(joinedload(Movie.streaming_platforms)).get(movie_id)
            return [p.to_dict(include_relationships=False) for p in movie.streaming_platforms] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting platforms for movie {movie_id}: {e}")
            return []

    def get_movie_categories(self, movie_id: int):
        """Get categories for a movie."""
        try:
            movie = Movie.query.options(joinedload(Movie.categories)).get(movie_id)
            return [c.to_dict(include_relationships=False) for c in movie.categories] if movie else []
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting categories for movie {movie_id}: {e}")
            return []

    def get_movies_by_category(self, category_id: int):
        """Get movies belonging to a specific category."""
        try:
            # Find movies linked via the association table or the direct foreign key
            category = Category.query.get(category_id)
            if not category: return []
            
            movies = Movie.query.filter(
                (Movie.categories.any(id=category_id)) | (Movie.category_id == category_id)
            ).options(joinedload(Movie.omdb_data)).all() # Fetch OMDB data too
            
            return [m.to_dict() for m in movies]
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting movies for category {category_id}: {e}")
            return []

    def get_all_categories(self):
        """Get all categories."""
        cats = self._all(Category)
        return [c.to_dict(include_relationships=False) for c in cats]

    def get_all_platforms(self):
        """Get all platforms."""
        platforms = self._all(StreamingPlatform)
        return [p.to_dict(include_relationships=False) for p in platforms]

    def get_movies_by_platform(self, platform_id: int):
        """Get movies available on a specific platform."""
        try:
            platform = StreamingPlatform.query.get(platform_id)
            if not platform: return []
            # Query movies linked via association table
            movies = Movie.query.filter(Movie.streaming_platforms.any(id=platform_id)).options(joinedload(Movie.omdb_data)).all()
            return [m.to_dict() for m in movies]
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting movies for platform {platform_id}: {e}")
            return []

    def get_all_categories_with_movies(self):
        """Get all categories, each with a list of associated movies (dictionaries)."""
        try:
            # Eager load movies and their OMDB data for each category
            categories = Category.query.options(
                subqueryload(Category.movies_m2m).joinedload(Movie.omdb_data), # For M2M relationship
                subqueryload(Category.movies).joinedload(Movie.omdb_data) # For FK relationship
            ).all()
            
            results = []
            for cat in categories:
                cat_dict = cat.to_dict(include_relationships=False)
                # Combine movies from both relationships, avoid duplicates
                all_cat_movies = {m.id: m for m in cat.movies_m2m}
                all_cat_movies.update({m.id: m for m in cat.movies})
                cat_dict['movies'] = [m.to_dict() for m in all_cat_movies.values()]
                results.append(cat_dict)
            return results
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting categories with movies: {e}")
            return []

    # --- Aggregation/Ranking Methods ---

    def get_top_rated_movies(self, limit=10, offset=0):
        """Get movies with the highest average rating from UserFavorite."""
        try:
            # Calculate average rating from UserFavorite table, filtering out non-rated entries
            avg_ratings = db.session.query(
                UserFavorite.movie_id,
                func.avg(UserFavorite.rating).label('average_rating')
            ).filter(UserFavorite.rating.isnot(None)) \
             .group_by(UserFavorite.movie_id) \
             .order_by(func.avg(UserFavorite.rating).desc()) \
             .limit(limit).offset(offset) \
             .subquery()

            # Join with Movie table to get movie details
            top_movies_query = db.session.query(Movie, avg_ratings.c.average_rating) \
                .join(avg_ratings, Movie.id == avg_ratings.c.movie_id) \
                .options(joinedload(Movie.omdb_data)) # Load OMDB data

            top_movies_results = top_movies_query.all()

            # Convert to list of dictionaries, adding average rating
            results = []
            for movie, avg_rating in top_movies_results:
                movie_dict = movie.to_dict()
                movie_dict['average_rating'] = round(avg_rating, 2) if avg_rating else None
                results.append(movie_dict)
                
            return results
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting top rated movies: {e}")
            return []

    def get_recent_commented_movies(self, limit=6, offset=0):
        """Get movies with the most recent comments from UserFavorite."""
        try:
            # Get UserFavorite entries with comments, ordered by composite key in descending order
            recent_comments = UserFavorite.query.filter(
                UserFavorite.comment.isnot(None), 
                UserFavorite.comment != ''
            ).options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                joinedload(UserFavorite.user).joinedload(User.avatar)
            ).order_by(
                UserFavorite.user_id.desc(),
                UserFavorite.movie_id.desc()
            )

            if limit is not None:
                recent_comments = recent_comments.limit(limit)
            if offset > 0:
                recent_comments = recent_comments.offset(offset)

            recent_comments = recent_comments.all()

            # Prepare the result in the format expected by the template
            results = []
            for entry in recent_comments:
                if entry.movie and entry.user:  # Ensure movie and user data are loaded
                    movie_dict = entry.movie.to_dict()  # Get base movie data
                    # Get avatar URLs safely, providing defaults
                    profile_avatar_url = entry.user.avatar.profile_image_url if entry.user.avatar else Avatar().profile_image_url
                    hero_avatar_url = entry.user.avatar.hero_image_url if entry.user.avatar else Avatar().hero_image_url

                    # Add comment-specific info
                    results.append({
                        'movie': movie_dict,
                        'comment_text': entry.comment,
                        'comment_user_name': entry.user.name,
                        'comment_user_id': entry.user.id,
                        'comment_user_avatar_url': profile_avatar_url,
                        'comment_user_hero_avatar_url': hero_avatar_url,
                        'composite_id': f"{entry.user_id}-{entry.movie_id}"  # Create a composite ID for sorting
                    })
            return results

        except SQLAlchemyError as e:
            logger.error(f"DB Error getting recent commented movies: {e}")
            return []

    def get_popular_movies(self, limit=10, offset=0):
        """Get movies based on the number of interactions (watched/watchlist/rated/favorited)."""
        try:
            # Base query for interaction counts
            interaction_query = db.session.query(
                UserFavorite.movie_id,
                func.count(UserFavorite.user_id).label('interaction_count')
            ).group_by(UserFavorite.movie_id) \
             .order_by(func.count(UserFavorite.user_id).desc())

            # Apply limit only if it's not None
            if limit is not None:
                interaction_query = interaction_query.limit(limit)
            if offset > 0:
                interaction_query = interaction_query.offset(offset)

            interaction_counts = interaction_query.subquery()

            # Join with Movie to get details
            popular_movies_query = db.session.query(Movie, interaction_counts.c.interaction_count) \
                .join(interaction_counts, Movie.id == interaction_counts.c.movie_id) \
                .options(
                    joinedload(Movie.omdb_data),
                    joinedload(Movie.favorites)  # Load favorites relationship
                )

            popular_movies_results = popular_movies_query.all()

            results = []
            for movie, count in popular_movies_results:
                movie_dict = movie.to_dict()
                movie_dict['interaction_count'] = count
                movie_dict['favorites'] = [fav.to_dict() for fav in movie.favorites]  # Include favorites data
                results.append(movie_dict)
            
            return results
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting popular movies: {e}")
            return []

    def get_most_loved_movies(self, limit=10, offset=0):
        """Get movies ranked by the number of times they were marked as favorite."""
        try:
            # Count favorite=True entries per movie_id
            favorite_counts = db.session.query(
                UserFavorite.movie_id,
                func.count(UserFavorite.user_id).label('favorite_count')
            ).filter(UserFavorite.favorite == True) \
             .group_by(UserFavorite.movie_id) \
             .order_by(func.count(UserFavorite.user_id).desc()) \
             .limit(limit).offset(offset) \
             .subquery()

            # Join with Movie to get details
            loved_movies_query = db.session.query(Movie, favorite_counts.c.favorite_count) \
                .join(favorite_counts, Movie.id == favorite_counts.c.movie_id) \
                .options(joinedload(Movie.omdb_data))

            loved_movies_results = loved_movies_query.all()

            results = []
            for movie, count in loved_movies_results:
                movie_dict = movie.to_dict()
                movie_dict['favorite_count'] = count
                results.append(movie_dict)
            
            return results
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting most loved movies: {e}", exc_info=True)
            return []

    def get_avg_movie_rating(self, movie_id):
        """Calculate the average user rating for a movie."""
        try:
            # Get all ratings for this movie where rating is not null
            ratings = UserFavorite.query.filter(
                UserFavorite.movie_id == movie_id,
                UserFavorite.rating.isnot(None)
            ).all()
            
            if not ratings:
                return None
                
            # Calculate average
            total = sum(entry.rating for entry in ratings if entry.rating)
            count = len(ratings)
            
            if count == 0:
                return None
                
            avg_rating = round(total / count, 1)
            logger.info(f"Calculated average rating for movie {movie_id}: {avg_rating} from {count} ratings")
            return avg_rating
        except Exception as e:
            logger.error(f"Error calculating average rating for movie {movie_id}: {e}")
            return None

    def get_friends_favorites(self, user_id, limit=10, offset=0):
        """DEPRECATED: Friends functionality removed."""
        logger.warning("get_friends_favorites called, but friends feature is removed.")
        return []

    def get_new_releases(self, limit=10, offset=0):
        """Get movies released recently based on OMDB 'Released' date."""
        # Note: OMDB 'Released' is a string, requires careful parsing or storing as date
        # This is a basic implementation assuming 'Released' can be somewhat sorted lexically (YYYY-MM-DD ideally)
        # or relies on Movie.year primarily. A proper date conversion/storage is recommended.
        try:
             # Try sorting by MovieOMDB.released if it's reasonably formatted, fallback to Movie.year
             # This might be slow without an index on MovieOMDB.released
             # A dedicated 'release_date' column in Movie table would be better.
            
             # Simple approach: Order by year, then maybe title?
            new_movies = Movie.query.options(joinedload(Movie.omdb_data)) \
                                   .order_by(Movie.year.desc(), Movie.name.asc()) \
                                   .limit(limit).offset(offset).all()
                                   
            # Alternative: Try sorting by OMDB released string (might not be accurate)
            # new_movies = Movie.query.join(MovieOMDB).options(joinedload(Movie.omdb_data)) \
            #                        .order_by(MovieOMDB.released.desc()) \
            #                        .limit(limit).offset(offset).all()

            return [m.to_dict() for m in new_movies]
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting new releases: {e}")
            return []

    # --- Category/Platform Management (Optional, depends on UI) ---
    def add_category(self, category_data):
        """Add a new category."""
        try:
            category = Category(**category_data)
            db.session.add(category)
            db.session.commit()
            return category.to_dict(include_relationships=False)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error adding category: {e}")
            return None

    def add_platform(self, platform_data):
        """Add a new streaming platform."""
        try:
            platform = StreamingPlatform(**platform_data)
            db.session.add(platform)
            db.session.commit()
            return platform.to_dict(include_relationships=False)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error adding platform: {e}")
            return None
