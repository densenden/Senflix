from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, logger, Rating, Avatar
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, subqueryload
from typing import Dict, List, Optional, Any
import os
from flask import current_app
from sqlalchemy.sql import func, and_

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
            else:
                # Update existing entry only if values are provided
                if watched is not None: fav.watched = watched
                if watchlist is not None: fav.watchlist = watchlist
                if favorite is not None: fav.favorite = favorite # Update favorite status
                if rating is not None: fav.rating = rating
                 # Allow clearing comment by passing empty string, but not None
                if comment is not None: fav.comment = comment
                # Set watched=True if user rates or comments? Common pattern.
                # if rating is not None or (comment is not None and comment.strip() != ''):
                #    fav.watched = True 

            db.session.commit()
            return True # Indicate success
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB Error upserting favorite for user {user_id}, movie {movie_id}: {e}")
            return False
        except Exception as e: # Catch potential non-DB errors
            db.session.rollback()
            logger.error(f"General error upserting favorite for user {user_id}, movie {movie_id}: {e}")
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
            return {'success': True, 'new_state': not current_value} # Return new state

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
            fav = UserFavorite.query.get((user_id, movie_id))
            return fav.to_dict() if fav else None # to_dict() now includes 'favorite'
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting favorite for user {user_id}, movie {movie_id}: {e}")
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
            # Find the latest comment timestamp for each movie that has comments
            latest_comment_subquery = db.session.query(
                UserFavorite.movie_id,
                func.max(UserFavorite.created_at).label('latest_comment_time') # Assuming created_at exists now
            ).filter(UserFavorite.comment.isnot(None), UserFavorite.comment != '') \
             .group_by(UserFavorite.movie_id) \
             .subquery()

            # Get UserFavorite entries matching the latest comment time for each movie
            recent_comments_query = db.session.query(UserFavorite) \
                .join(latest_comment_subquery, and_(
                    UserFavorite.movie_id == latest_comment_subquery.c.movie_id,
                    UserFavorite.created_at == latest_comment_subquery.c.latest_comment_time # Assuming created_at exists
                )) \
                .options(
                    joinedload(UserFavorite.movie).joinedload(Movie.omdb_data), # Load movie->omdb
                    joinedload(UserFavorite.user).joinedload(User.avatar) # Load user->avatar
                ) \
                .order_by(latest_comment_subquery.c.latest_comment_time.desc()) \
                .limit(limit).offset(offset)

            recent_comments = recent_comments_query.all()

            # Prepare the result in the format expected by the template
            results = []
            for entry in recent_comments:
                if entry.movie and entry.user: # Ensure movie and user data are loaded
                    movie_dict = entry.movie.to_dict() # Get base movie data
                    # Get avatar URLs safely, providing defaults
                    profile_avatar_url = entry.user.avatar.profile_image_url if entry.user.avatar else Avatar().profile_image_url
                    hero_avatar_url = entry.user.avatar.hero_image_url if entry.user.avatar else Avatar().hero_image_url # Get hero URL

                    # Add comment-specific info
                    results.append({
                        'movie': movie_dict, 
                        'comment_text': entry.comment, 
                        'comment_user_name': entry.user.name,
                        'comment_user_id': entry.user.id,
                        'comment_user_avatar_url': profile_avatar_url, # Existing profile avatar
                        'comment_user_hero_avatar_url': hero_avatar_url # Added hero avatar URL
                        # Add the timestamp if needed
                        # 'comment_created_at': entry.created_at.isoformat() if entry.created_at else None
                    })
            return results

        except AttributeError:
             # Fallback if 'created_at' doesn't exist on UserFavorite
             logger.warning("UserFavorite model missing 'created_at'. Fetching recent comments without sorting by time.")
             # Simpler fallback: Get any 6 comments, ordered perhaps by user/movie ID
             recent_comments = UserFavorite.query.filter(
                   UserFavorite.comment.isnot(None), UserFavorite.comment != ''
               ).options(
                   joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                   joinedload(UserFavorite.user).joinedload(User.avatar)
               ).order_by(UserFavorite.user_id.desc(), UserFavorite.movie_id.desc()) \
                .limit(limit).offset(offset).all()
             # Prepare results as above...
             results = []
             for entry in recent_comments:
                  if entry.movie and entry.user:
                      movie_dict = entry.movie.to_dict()
                      # Get avatar URLs safely, providing defaults
                      profile_avatar_url = entry.user.avatar.profile_image_url if entry.user.avatar else Avatar().profile_image_url
                      hero_avatar_url = entry.user.avatar.hero_image_url if entry.user.avatar else Avatar().hero_image_url # Get hero URL (also in fallback)
                      
                      results.append({
                          'movie': movie_dict,
                          'comment_text': entry.comment,
                          'comment_user_name': entry.user.name,
                          'comment_user_id': entry.user.id,
                          'comment_user_avatar_url': profile_avatar_url, # Existing profile avatar
                          'comment_user_hero_avatar_url': hero_avatar_url # Added hero avatar URL (also in fallback)
                      })
             return results
            
        except SQLAlchemyError as e:
            logger.error(f"DB Error getting recent commented movies: {e}")
            return []

    def get_popular_movies(self, limit=10, offset=0):
        """Get movies based on the number of interactions (watched/watchlist/rated/favorited)."""
        try:
            # Count interactions per movie_id
            interaction_counts = db.session.query(
                UserFavorite.movie_id,
                func.count(UserFavorite.user_id).label('interaction_count')
            ).group_by(UserFavorite.movie_id) \
             .order_by(func.count(UserFavorite.user_id).desc()) \
             .limit(limit).offset(offset) \
             .subquery()

            # Join with Movie to get details
            popular_movies_query = db.session.query(Movie, interaction_counts.c.interaction_count) \
                .join(interaction_counts, Movie.id == interaction_counts.c.movie_id) \
                .options(joinedload(Movie.omdb_data))

            popular_movies_results = popular_movies_query.all()

            results = []
            for movie, count in popular_movies_results:
                movie_dict = movie.to_dict()
                movie_dict['interaction_count'] = count
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
