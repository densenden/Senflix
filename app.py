import os
from functools import wraps
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from datamanager.db_manager import SQLiteDataManager
from datamanager.interface import User, Avatar, Category, Movie, StreamingPlatform
from datamanager.omdb_manager import OMDBManager

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

data_manager = SQLiteDataManager()
data_manager.init_app(app)
omdb_manager = OMDBManager(data_manager)

login_manager = LoginManager(app)
login_manager.login_view = 'user_selection'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    return dict(get_user=lambda uid: data_manager.get_user_by_id(uid))


def require_fields(fields, redirect_endpoint):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            missing = [f for f in fields if not request.form.get(f)]
            if missing:
                flash(f"Bitte ausgefüllt: {', '.join(missing)}", 'error')
                return redirect(url_for(redirect_endpoint))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def ajax_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            return jsonify({'success': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    return wrapped

@app.route('/')
def user_selection():
    return render_template('user_selection.html', users=data_manager.get_all_users(), available_avatars=Avatar.query.all(), current_user=current_user)

@app.route('/create_user', methods=['POST'])
@require_fields(['avatar','description'], 'user_selection')
def create_user():
    avatar_id = int(request.form['avatar'])
    desc = request.form['description']
    user = data_manager.add_user(name=f"User{datetime.utcnow().timestamp()}", whatsapp_number='', description=desc, avatar_id=avatar_id)
    flash('Profil erstellt!' if user else 'Fehler beim Erstellen', 'success' if user else 'error')
    return redirect(url_for('user_selection'))

@app.route('/select_user/<int:user_id>')
def select_user(user_id):
    user = User.query.get(user_id)
    if user: login_user(user)
    return redirect(url_for('movies'))

@app.route('/movies')
@login_required
def movies():
    genre = request.args.get('genre', type=int)
    genres = data_manager.get_all_categories_with_movies()
    platforms = data_manager.get_all(StreamingPlatform)
    if genre:
        return render_template('movies.html', movies=data_manager.get_movies_by_category(genre), genres=genres, platforms=platforms, current_genre=genre)
    return render_template('movies.html', new_releases=data_manager.get_movies_by_category(1), popular_movies=data_manager.get_user_favorites(current_user.id), genres=genres, platforms=platforms)

@app.route('/movie/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = data_manager.get_movie_data(movie_id)
    if not movie:
        flash('Nicht gefunden', 'error')
        return redirect(url_for('movies'))
    return render_template('movie_detail.html', movie=movie)

@app.route('/toggle_watchlist/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watchlist(movie_id):
    return data_manager.upsert_favorite(current_user.id, movie_id, watchlist=True)

@app.route('/toggle_watched/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watched(movie_id):
    return data_manager.upsert_favorite(current_user.id, movie_id, watched=True)

@app.route('/rate_movie', methods=['POST'])
@login_required
@ajax_route
def rate_movie():
    movie_id = int(request.form['movie_id'])
    rating = float(request.form['rating'])
    comment = request.form.get('comment', '')
    return data_manager.upsert_favorite(current_user.id, movie_id, rating=rating, comment=comment)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', stats=data_manager.get_user_data(current_user.id)['favorites'])

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('user_selection'))

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('movies'))
    results = []
    for m in data_manager.get_all_movies():
        if q.lower() in m['name'].lower():
            details = data_manager.get_movie_data(m['id'])
            details['omdb'] = omdb_manager.get_omdb_data(m['id']) or {}
            results.append(details)
    return render_template('search_results.html', query=q, results=results)

@app.route('/users')
def users():
    groups = {i:{'name':f'Avatar {i}','users':[], 'img_url':url_for('static', filename=f'avatars/hero/avatar_{i}.jpg')} for i in range(1,12)}
    for u in data_manager.get_all_users():
        aid=u['avatar_id']
        groups[aid]['users'].append(u)
    active=[g for g in groups.values() if g['users']]
    return render_template('users.html', avatar_groups=active)

@app.route('/users/<int:user_id>')
def user_movies(user_id):
    user = data_manager.get_user_data(user_id)
    if not user:
        flash('User nicht gefunden','error')
        return redirect(url_for('users'))
    return render_template('user_movies.html', user=user)

@app.route('/users/<int:user_id>/add_movie', methods=['GET','POST'])
@login_required
def add_movie(user_id):
    if request.method=='POST':
        mid=int(request.form['movie_id'])
        watched='watched' in request.form
        rating=float(request.form['rating']) if request.form.get('rating') else None
        comment=request.form.get('comment')
        data_manager.upsert_favorite(user_id, mid, watched=watched, rating=rating, comment=comment)
        flash('Gespeichert','success')
        return redirect(url_for('user_movies', user_id=user_id))
    return render_template('add_movie.html', user_id=user_id, movies=data_manager.get_all_movies())

@app.route('/users/<int:user_id>/update_movie/<int:movie_id>', methods=['GET','POST'])
@login_required
def update_movie(user_id, movie_id):
    fav = next((f for f in data_manager.get_user_favorites(user_id) if f['movie_id']==movie_id), None)
    if not fav:
        flash('Nicht in Favoriten','error')
        return redirect(url_for('user_movies', user_id=user_id))
    if request.method=='POST':
        data_manager.upsert_favorite(user_id, movie_id, watched='watched' in request.form, rating=float(request.form.get('rating')) if request.form.get('rating') else None, comment=request.form.get('comment'))
        flash('Aktualisiert','success')
        return redirect(url_for('user_movies', user_id=user_id))
    return render_template('update_movie.html', user_id=user_id, movie=fav)

@app.route('/users/<int:user_id>/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(user_id, movie_id):
    data_manager.remove_favorite(user_id, movie_id)
    flash('Entfernt','success')
    return redirect(url_for('user_movies', user_id=user_id))

if __name__=='__main__':
    app.run(debug=True, port=5001)