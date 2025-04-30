from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, MovieOMDB, logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, subqueryload
from typing import Dict, List, Optional, Any
import os

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

    def add_user(self, name: str, whatsapp_number: str, avatar_id: Optional[int] = 1):
        try:
            u = User(name=name, whatsapp_number=whatsapp_number, avatar_id=avatar_id)
            db.session.add(u)
            db.session.commit()
            return u.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding user {name}: {e}")
            return None

    def get_all_movies(self):
        options = [
            joinedload(Movie.omdb_data),
            subqueryload(Movie.platforms),
            subqueryload(Movie.categories)
        ]
        movies = self._all(Movie, options=options)
        return [m.to_dict() for m in movies]

    def get_movie_data(self, movie_id):
        try:
            movie = Movie.query.options(
                joinedload(Movie.omdb_data),
                subqueryload(Movie.platforms),
                subqueryload(Movie.categories)
            ).filter_by(id=movie_id).first()
            return movie.to_dict() if movie else None
        except SQLAlchemyError as e:
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
                movie.platforms.extend(platforms)
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
                movie.platforms = platforms

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

    def get_user_favorites(self, user_id: int):
        try:
            favorites_with_movies = db.session.query(UserFavorite).options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                joinedload(UserFavorite.movie).subqueryload(Movie.platforms),
                joinedload(UserFavorite.movie).subqueryload(Movie.categories)
            ).filter(UserFavorite.user_id == user_id).all()

            movies_list = []
            for fav in favorites_with_movies:
                if fav.movie:
                    movie_dict = fav.movie.to_dict()
                    movie_dict['watched'] = fav.watched
                    movie_dict['comment'] = fav.comment
                    movie_dict['rating'] = fav.rating
                    movie_dict['watchlist'] = fav.watchlist
                    movie_dict['favorite_created_at'] = fav.created_at.isoformat() if fav.created_at else None
                    movie_dict['favorite_updated_at'] = fav.updated_at.isoformat() if fav.updated_at else None
                    movie_dict['movie_id'] = fav.movie_id
                    movies_list.append(movie_dict)
            return movies_list
        except SQLAlchemyError as e:
            logger.error(f"Error getting favorites for user {user_id}: {e}")
            return []

    def get_movie_platforms(self, movie_id: int):
        try:
            movie = Movie.query.options(
                subqueryload(Movie.platforms)
            ).filter_by(id=movie_id).first()
            return [p.to_dict() for p in movie.platforms] if movie else []
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
                subqueryload(Category.movies).subqueryload(Movie.platforms),
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
                subqueryload(Category.movies).subqueryload(Movie.platforms),
                subqueryload(Category.movies).subqueryload(Movie.categories)
            ).all()

            result = []
            for cat in categories:
                cat_dict = cat.to_dict()
                cat_dict['movies'] = [m.to_dict() for m in cat.movies]
                result.append(cat_dict)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting all categories with movies: {e}")
            return []

    def get_all_platforms(self):
        platforms = self._all(StreamingPlatform)
        return [p.to_dict() for p in platforms]

    def get_all_categories(self):
        categories = self._all(Category)
        return [c.to_dict() for c in categories]

    def get_movies_by_platform(self, platform_id: int):
        try:
            platform = StreamingPlatform.query.options(
                subqueryload(StreamingPlatform.movies).joinedload(Movie.omdb_data),
                subqueryload(StreamingPlatform.movies).subqueryload(Movie.platforms),
                subqueryload(StreamingPlatform.movies).subqueryload(Movie.categories)
            ).filter_by(id=platform_id).first()
            return [m.to_dict() for m in platform.movies] if platform else []
        except SQLAlchemyError as e:
            logger.error(f"Error getting movies for platform {platform_id}: {e}")
            return []

    def get_top_rated_movies(self, limit: int = 10):
        try:
            movies = Movie.query.outerjoin(UserFavorite).group_by(Movie.id).order_by(
                db.func.avg(UserFavorite.rating).desc().nullslast()
            ).options(
                joinedload(Movie.omdb_data),
                subqueryload(Movie.platforms),
                subqueryload(Movie.categories)
            ).limit(limit).all()
            return [m.to_dict() for m in movies]
        except SQLAlchemyError as e:
            logger.error(f"Error getting top rated movies: {e}")
            return []

    def get_recent_commented_movies(self, limit: int = 10):
        try:
            subq = db.session.query(UserFavorite.movie_id, db.func.max(UserFavorite.updated_at).label('latest_update'))\
                .filter(UserFavorite.comment != None, UserFavorite.comment != '')\
                .group_by(UserFavorite.movie_id)\
                .order_by(db.text('latest_update DESC'))\
                .limit(limit)\
                .subquery()

            movies = Movie.query.join(subq, Movie.id == subq.c.movie_id)\
                .options(
                    joinedload(Movie.omdb_data),
                    subqueryload(Movie.platforms),
                    subqueryload(Movie.categories)
                )\
                .order_by(db.text('latest_update DESC'))\
                .all()

            return [m.to_dict() for m in movies]
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent commented movies: {e}")
            return []

    def get_popular_movies(self, limit: int = 10):
        try:
            movies = Movie.query.outerjoin(UserFavorite).group_by(Movie.id).order_by(
                db.func.count(UserFavorite.user_id).desc()
            ).options(
                joinedload(Movie.omdb_data),
                subqueryload(Movie.platforms),
                subqueryload(Movie.categories)
            ).limit(limit).all()
            return [m.to_dict() for m in movies]
        except SQLAlchemyError as e:
            logger.error(f"Error getting popular movies: {e}")
            return []

    def get_friends_favorites(self, user_id: int, limit: int = 10):
        try:
            favorites = UserFavorite.query.filter(
                UserFavorite.user_id != user_id,
                UserFavorite.watched == True
            ).order_by(
                UserFavorite.updated_at.desc()
            ).options(
                joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                joinedload(UserFavorite.movie).subqueryload(Movie.platforms),
                joinedload(UserFavorite.movie).subqueryload(Movie.categories)
            ).limit(limit * 2)

            unique_movies = {}
            for fav in favorites:
                if fav.movie_id not in unique_movies and fav.movie:
                    movie_dict = fav.movie.to_dict()
                    unique_movies[fav.movie_id] = movie_dict
                if len(unique_movies) >= limit:
                    break

            return list(unique_movies.values())
        except SQLAlchemyError as e:
            logger.error(f"Error getting friends' favorites for user {user_id}: {e}")
            return []

    def add_rating(self, user_id: int, movie_id: int, rating: float, comment: Optional[str] = None):
        success = self.upsert_favorite(user_id, movie_id, rating=rating, comment=comment)
        if success:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            return fav.to_dict() if fav else None
        return None

    def get_movie_ratings(self, movie_id: int):
        try:
            favs = UserFavorite.query.filter(
                UserFavorite.movie_id == movie_id,
                UserFavorite.rating != None
            ).options(
                joinedload(UserFavorite.user).joinedload(User.avatar)
            ).all()
            return [f.to_dict() for f in favs]
        except SQLAlchemyError as e:
            logger.error(f"Error getting ratings for movie {movie_id}: {e}")
            return []

    def get_movie_average_rating(self, movie_id: int):
        try:
            avg = db.session.query(
                db.func.avg(UserFavorite.rating)
            ).filter(
                UserFavorite.movie_id == movie_id,
                UserFavorite.rating != None
            ).scalar()
            return round(avg, 2) if avg is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Error calculating average rating for movie {movie_id}: {e}")
            return None

    def add_favorite(self, user_id: int, movie_id: int, watched: bool = False, comment: Optional[str] = None, rating: Optional[float] = None, watchlist: bool = False):
        return self.upsert_favorite(user_id=user_id, movie_id=movie_id, watched=watched, comment=comment, rating=rating, watchlist=watchlist)

    def get_user_data(self, user_id: int):
        try:
            user = User.query.options(
                joinedload(User.avatar),
                subqueryload(User.favorites).joinedload(UserFavorite.movie).joinedload(Movie.omdb_data),
                subqueryload(User.favorites).joinedload(UserFavorite.movie).subqueryload(Movie.platforms),
                subqueryload(User.favorites).joinedload(UserFavorite.movie).subqueryload(Movie.categories)
            ).filter_by(id=user_id).first()

            if not user:
                return None

            user_data = {
                'id': user.id,
                'name': user.name,
                'whatsapp_number': user.whatsapp_number,
                'avatar_id': user.avatar_id,
                'avatar': user.avatar.to_dict() if user.avatar else None,
                'favorites': []
            }

            movies_list = []
            for fav in user.favorites:
                if fav.movie:
                    movie_dict = fav.movie.to_dict()
                    movie_dict['watched'] = fav.watched
                    movie_dict['comment'] = fav.comment
                    movie_dict['rating'] = fav.rating
                    movie_dict['watchlist'] = fav.watchlist
                    movie_dict['favorite_created_at'] = fav.created_at.isoformat() if fav.created_at else None
                    movie_dict['favorite_updated_at'] = fav.updated_at.isoformat() if fav.updated_at else None
                    movie_dict['movie_id'] = fav.movie_id
                    movies_list.append(movie_dict)

            user_data['favorites'] = movies_list
            return user_data
        except SQLAlchemyError as e:
            logger.error(f"Error getting user data for user {user_id}: {e}")
            return None
        except AttributeError:
            logger.error(f"Error getting user data for user {user_id}: Avatar model might be missing .to_dict()")
            return None
