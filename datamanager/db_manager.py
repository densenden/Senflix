from .interface import db, DataManagerInterface, User, Movie, Category, StreamingPlatform, UserFavorite, logger
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Any
import os

class SQLiteDataManager(DataManagerInterface):
    def __init__(self):
        # Use shared db instance from interface
        self.db = db

    def init_app(self, app):
        # Only set the DB URI if not already set (so tests can override)
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/senflix.sqlite'))
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        with app.app_context():
            db.create_all()
        with app.app_context():
            self.db.create_all()

    def _get(self, model, **filters):
        try:
            return model.query.filter_by(**filters).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__}: {e}")
            return None

    def _all(self, model):
        try:
            return [m.to_dict() for m in model.query.all()]
        except SQLAlchemyError as e:
            logger.error(f"Error listing {model.__name__}: {e}")
            return []

    def get_all_users(self):
        return User.query.all()

    def get_user_by_id(self, user_id):
        user = self._get(User, id=user_id)
        return user.to_dict() if user else None

    def add_user(self, name: str, whatsapp_number: str, avatar_id: Optional[int]):
        try:
            u = User(name=name, whatsapp_number=whatsapp_number, avatar_id=avatar_id)
            db.session.add(u); db.session.commit()
            return u.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error adding user: {e}"); return None

    def get_all_movies(self): return self._all(Movie)
    def get_movie_data(self, movie_id):
        m = self._get(Movie, id=movie_id)
        return m.to_dict() if m else None

    def add_movie(self, data):
        try:
            m = Movie(**data); db.session.add(m); db.session.commit(); return m.to_dict()
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error adding movie: {e}"); return None

    def update_movie(self, mid, data):
        try:
            m = self._get(Movie, id=mid)
            if m:
                for k,v in data.items(): setattr(m,k,v)
                db.session.commit(); return m.to_dict()
            return None
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error updating movie: {e}"); return None

    def delete_movie(self, mid):
        try:
            m = self._get(Movie, id=mid)
            if m: db.session.delete(m); db.session.commit(); return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error deleting movie: {e}"); return False

    def upsert_favorite(self, user_id, movie_id, watched=False, comment=None, rating=None, watchlist=False):
        try:
            fav = UserFavorite.query.filter_by(user_id=user_id,movie_id=movie_id).first() or UserFavorite(user_id=user_id,movie_id=movie_id)
            fav.watched, fav.comment, fav.rating, fav.watchlist = watched, comment, rating, watchlist
            db.session.add(fav); db.session.commit(); return True
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error upserting favorite: {e}"); return False

    def remove_favorite(self, user_id, movie_id):
        try:
            fav = self._get(UserFavorite, user_id=user_id, movie_id=movie_id)
            if fav: db.session.delete(fav); db.session.commit(); return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"Error removing favorite: {e}"); return False

    def get_user_favorites(self, user_id):
        try:
            # Return movie dicts, not just favorite metadata
            favorites = UserFavorite.query.filter_by(user_id=user_id).all()
            movies = []
            for f in favorites:
                m = self._get(Movie, id=f.movie_id)
                if m:
                    movie_dict = m.to_dict()
                    # Attach favorite metadata to movie dict
                    movie_dict['watched'] = f.watched
                    movie_dict['comment'] = f.comment
                    movie_dict['rating'] = f.rating
                    movie_dict['watchlist'] = f.watchlist
                    movie_dict['movie_id'] = f.movie_id  # for clarity
                    movies.append(movie_dict)
            return movies
        except SQLAlchemyError as e:
            logger.error(f"Error getting favorites: {e}"); return []

    def get_movie_platforms(self, movie_id):
        m = self._get(Movie, id=movie_id)
        return [p.to_dict() for p in m.platforms] if m else []

    def get_movie_categories(self, movie_id):
        m = self._get(Movie, id=movie_id)
        return [c.to_dict() for c in m.categories] if m else []

    def get_movies_by_category(self, cid):
        cat = self._get(Category, id=cid)
        return [m.to_dict() for m in cat.movies] if cat else []

    def get_all_categories_with_movies(self):
        cats = Category.query.all()
        return [dict(**c.to_dict(), movies=self.get_movies_by_category(c.id)) for c in cats]

    def get_all_platforms(self):
        return self._all(StreamingPlatform)

    # CATEGORY & PLATFORM METHODS
    def get_all_categories(self):
        return self._all(Category)

    # MOVIE FILTERING METHODS
    def get_movies_by_platform(self, platform_id):
        platform = self._get(StreamingPlatform, id=platform_id)
        return [m.to_dict() for m in platform.movies] if platform else []

    def get_top_rated_movies(self, limit=10):
        movies = Movie.query.outerjoin(UserFavorite).group_by(Movie.id).order_by(db.func.avg(UserFavorite.rating).desc()).limit(limit).all()
        return [m.to_dict() for m in movies]

    def get_recent_commented_movies(self, limit=10):
        movies = Movie.query.join(UserFavorite).filter(UserFavorite.comment != None).order_by(UserFavorite.user_id.desc()).limit(limit).all()
        return [m.to_dict() for m in movies]

    def get_popular_movies(self, limit=10):
        movies = Movie.query.outerjoin(UserFavorite).group_by(Movie.id).order_by(db.func.count(UserFavorite.user_id).desc()).limit(limit).all()
        return [m.to_dict() for m in movies]

    # SOCIAL METHODS
    def get_friends_favorites(self, user_id, limit=10):
        user = self._get(User, id=user_id)
        if not user:
            return []
        # Example: friends = all users except current user
        friends = User.query.filter(User.id != user_id).all()
        friend_ids = [f.id for f in friends]
        favs = UserFavorite.query.filter(UserFavorite.user_id.in_(friend_ids), UserFavorite.watched==True).order_by(UserFavorite.user_id.desc()).limit(limit).all()
        movie_ids = list({f.movie_id for f in favs})
        return [self.get_movie_data(mid) for mid in movie_ids]

    # RATING & COMMENT METHODS
    def add_rating(self, user_id, movie_id, rating, comment=None):
        fav = UserFavorite.query.filter_by(user_id=user_id, movie_id=movie_id).first()
        if not fav:
            fav = UserFavorite(user_id=user_id, movie_id=movie_id)
            db.session.add(fav)
        fav.rating = rating
        fav.comment = comment
        db.session.commit()
        return fav.to_dict()

    def get_movie_ratings(self, movie_id):
        favs = UserFavorite.query.filter_by(movie_id=movie_id).filter(UserFavorite.rating != None).all()
        return [f.to_dict() for f in favs]

    def get_movie_average_rating(self, movie_id):
        avg = db.session.query(db.func.avg(UserFavorite.rating)).filter_by(movie_id=movie_id).scalar()
        return round(avg, 2) if avg else None

    # Implement abstract methods
    def add_favorite(self, user_id, movie_id, watched=False, comment=None, rating=None, watchlist=False):
        return self.upsert_favorite(user_id=user_id, movie_id=movie_id, watched=watched, comment=comment, rating=rating, watchlist=watchlist)

    def get_user_data(self, user_id):
        user = self._get(User, id=user_id)
        if not user:
            return None
        data = user.to_dict()
        data['favorites'] = self.get_user_favorites(user_id)
        return data
