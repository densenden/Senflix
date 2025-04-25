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
            return [f.to_dict() for f in UserFavorite.query.filter_by(user_id=user_id).all()]
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
