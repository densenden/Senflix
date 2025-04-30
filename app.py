import os
from functools import wraps
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from datamanager.db_manager import SQLiteDataManager
from datamanager.interface import User, Avatar, Category, Movie, StreamingPlatform, UserFavorite
from datamanager.omdb_manager import OMDBManager
from sqlalchemy.orm import joinedload

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Setze den Datenbankpfad
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/senflix.sqlite'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"[DB DEBUG] SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

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
                flash(f"Please fill out: {', '.join(missing)}", 'error')
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
    users = User.query.all()  # Pass SQLAlchemy objects to Jinja
    print(f"[DEBUG] users: {users}")
    available_avatars = Avatar.query.all()
    print(f"[DEBUG] available_avatars: {available_avatars}")
    return render_template('user_selection.html', users=users, available_avatars=available_avatars, current_user=current_user)

@app.route('/create_user', methods=['POST'])
@require_fields(['avatar','name','whatsapp_number'], 'user_selection')
def create_user():
    avatar_id = int(request.form['avatar'])
    name = request.form['name']
    whatsapp_number = request.form['whatsapp_number']
    user = data_manager.add_user(name=name, whatsapp_number=whatsapp_number, avatar_id=avatar_id)
    flash('Profile created!' if user else 'Error creating profile', 'success' if user else 'error')
    return redirect(url_for('user_selection'))

@app.route('/select_user/<int:user_id>')
def select_user(user_id):
    user = User.query.get(user_id)
    if user: login_user(user)
    return redirect(url_for('movies'))

@app.route('/movies')
def movies():
    
    # Get all required movie lists
    try:
        new_releases = data_manager.get_new_releases(limit=10)  # Get 10 most recent movies
        popular_movies = data_manager.get_popular_movies(limit=10)
        top_rated = data_manager.get_top_rated_movies(limit=10)
        recent_comments = data_manager.get_recent_commented_movies(limit=5)
        all_movies = data_manager.get_all_movies()  # Alle Filme für Kategoriedarstellungen
        
        # Debug prints with detailed movie structure
        if new_releases:
            print("[DEBUG] Sample New Release Movie Structure:", new_releases[0])
            # Überprüfe OMDB-Daten im ersten Film
            omdb_data = new_releases[0].get('omdb_data', {})
            print(f"[DEBUG] OMDB Daten vorhanden: {omdb_data is not None}")
            print(f"[DEBUG] OMDB Daten Typ: {type(omdb_data)}")
            if omdb_data:
                poster_img = omdb_data.get('poster_img')
                print(f"[DEBUG] Poster Bild: {poster_img}")
                print(f"[DEBUG] Vollständige OMDB Daten: {omdb_data}")
            # Prüfe, ob omdb_data und poster_img vorhanden sind
            omdb_data = new_releases[0].get('omdb_data', {})
            poster_img = omdb_data.get('poster_img', 'FEHLT!')
            print(f"[DEBUG] Erstes Film omdb_data: {omdb_data}")
            print(f"[DEBUG] Erstes Film poster_img: {poster_img}")

        if popular_movies:
            print("[DEBUG] Sample Popular Movie Structure:", popular_movies[0])
            # Prüfe, ob omdb_data und poster_img vorhanden sind
            omdb_data = popular_movies[0].get('omdb_data', {})
            poster_img = omdb_data.get('poster_img', 'FEHLT!')
            print(f"[DEBUG] Beliebter Film omdb_data: {omdb_data}")
            print(f"[DEBUG] Beliebter Film poster_img: {poster_img}")
        
        if top_rated:
            print("[DEBUG] Sample Top Rated Movie Structure:", top_rated[0])
        if recent_comments:
            print("[DEBUG] Sample Recent Comment Movie Structure:", recent_comments[0])
        
        # Get friends' favorites if user is logged in
        friends_favorites = []
        if current_user.is_authenticated:
            friends_favorites = data_manager.get_friends_favorites(current_user.id, limit=10)
            if friends_favorites:
                print("[DEBUG] Sample Friends Favorite Structure:", friends_favorites[0])
        
        categories = data_manager.get_all_categories()
        platforms = data_manager.get_all_platforms()
        
        if categories:
            print("[DEBUG] Sample Category Structure:", categories[0])
        if platforms:
            print("[DEBUG] Sample Platform Structure:", platforms[0])
    except Exception as e:
        print(f"[ERROR] Fehler beim Laden der Filmlisten: {str(e)}")
        new_releases = []
        popular_movies = []
        top_rated = []
        recent_comments = []
        friends_favorites = []
        all_movies = []
        categories = []
        platforms = []
    


    return render_template('movies.html',
                         movies=all_movies,
                         new_releases=new_releases,
                         popular_movies=popular_movies,
                         friends_favorites=friends_favorites,
                         top_rated=top_rated,
                         recent_comments=recent_comments,
                         categories=categories,
                         platforms=platforms)

@app.route('/movie/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = data_manager.get_movie_data(movie_id)
    if not movie:
        flash('Not found', 'error')
        return redirect(url_for('movies'))
    # Get all users who watched this movie
    watched_entries = UserFavorite.query.filter_by(movie_id=movie_id, watched=True).all()
    watched_users = []
    for entry in watched_entries:
        user = User.query.get(entry.user_id)
        if user:
            avatar = Avatar.query.get(user.avatar_id)
            watched_users.append({
                'id': user.id,
                'name': user.name,
                'avatar_url': avatar.profile_image_url if avatar else '/static/avatars/default.png',
                'rating': entry.rating
            })
    # Get OMDB info if present
    omdb_data = movie.get('omdb_data') if isinstance(movie, dict) else None
    return render_template('movie_detail.html', movie=movie, watched_users=watched_users, omdb_data=omdb_data, current_user=current_user)

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
    avatars = Avatar.query.all()
    avatar_groups = []
    for avatar in avatars:
        users = avatar.users.all()
        if not users:
            continue
        group = {
            'name': avatar.name,
            'img_url': url_for('static', filename=avatar.hero_image_url),
            'users': [data_manager.get_user_data(u.id) for u in users]
        }
        avatar_groups.append(group)
    return render_template('users.html', avatar_groups=avatar_groups)

@app.route('/users/<int:user_id>')
@login_required
def user_profile(user_id):
    user = data_manager.get_user_data(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('movies'))
    # Separate favorites into watched and watchlist
    favorites = user.get('favorites', [])
    watched = [f for f in favorites if f.get('watched')]
    watchlist = [f for f in favorites if f.get('watchlist')]
    # Last comments (show up to 3, most recent last)
    comments = [f for f in favorites if f.get('comment')]
    last_comments = comments[-3:] if comments else []
    return render_template(
        'user_movies.html',
        user=user,
        watched=watched,
        watchlist=watchlist,
        last_comments=last_comments
    )

@app.route('/users/<int:user_id>/add_movie', methods=['GET','POST'])
@login_required
def add_movie(user_id):
    if request.method=='POST':
        mid=int(request.form['movie_id'])
        watched='watched' in request.form
        rating=float(request.form['rating']) if request.form.get('rating') else None
        comment=request.form.get('comment')
        data_manager.upsert_favorite(user_id, mid, watched=watched, rating=rating, comment=comment)
        flash('Saved','success')
        return redirect(url_for('user_profile', user_id=user_id))
    return render_template('add_movie.html', user_id=user_id, movies=data_manager.get_all_movies())

@app.route('/users/<int:user_id>/update_movie/<int:movie_id>', methods=['GET','POST'])
@login_required
def update_movie(user_id, movie_id):
    fav = next((f for f in data_manager.get_user_favorites(user_id) if f['movie_id']==movie_id), None)
    if not fav:
        flash('Not in favorites','error')
        return redirect(url_for('user_profile', user_id=user_id))
    if request.method=='POST':
        data_manager.upsert_favorite(user_id, movie_id, watched='watched' in request.form, rating=float(request.form.get('rating')) if request.form.get('rating') else None, comment=request.form.get('comment'))
        flash('Updated','success')
        return redirect(url_for('user_profile', user_id=user_id))
    return render_template('update_movie.html', user_id=user_id, movie=fav)

@app.route('/users/<int:user_id>/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(user_id, movie_id):
    data_manager.remove_favorite(user_id, movie_id)
    flash('Removed','success')
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/category/<int:category_id>')
@login_required
def category_detail(category_id):
    # Get the category object (for name, img, etc.)
    category_obj = Category.query.get(category_id)
    if not category_obj:
        flash('Category not found', 'error')
        return redirect(url_for('movies'))
    movies = data_manager.get_movies_by_category(category_id)
    category = category_obj.to_dict()
    category['movies'] = movies
    return render_template('category_detail.html', category=category, current_user=current_user)

if __name__=='__main__':
    app.run(debug=True, port=5002)