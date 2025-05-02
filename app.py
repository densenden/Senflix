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

# Database setup
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/senflix.sqlite'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# print(f"[DB DEBUG] SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}") # Removed debug print

data_manager = SQLiteDataManager()
data_manager.init_app(app)
omdb_manager = OMDBManager(data_manager)

# Login manager setup
login_manager = LoginManager(app)
login_manager.login_view = 'user_selection'

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    """Inject utility functions into Jinja context."""
    return dict(get_user=lambda uid: data_manager.get_user_by_id(uid))

# --- Decorators ---

def require_fields(fields, redirect_endpoint):
    """Decorator to ensure required form fields are present."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            missing = [field for field in fields if not request.form.get(field)]
            if missing:
                flash(f"Please fill out: {", ".join(missing)}", 'error')
                return redirect(url_for(redirect_endpoint))
            return f(*args, **kwargs)
        return wrapped
    return decorator

def ajax_route(f):
    """Decorator to handle AJAX requests, returning JSON responses."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            return jsonify({'success': result})
        except Exception as e:
            # Log the exception for debugging if needed
            # logger.error(f"AJAX Error in {f.__name__}: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 400
    return wrapped

# --- Routes ---

@app.route('/')
def user_selection():
    """Display user selection screen."""
    users = User.query.all()
    available_avatars = Avatar.query.all()
    # print(f"[DEBUG] users: {users}") # Removed debug print
    # print(f"[DEBUG] available_avatars: {available_avatars}") # Removed debug print
    return render_template('user_selection.html', users=users, available_avatars=available_avatars, current_user=current_user)

@app.route('/create_user', methods=['POST'])
@require_fields(['avatar','name','whatsapp_number'], 'user_selection')
def create_user():
    """Handle user creation form submission."""
    avatar_id = int(request.form['avatar'])
    name = request.form['name']
    whatsapp_number = request.form['whatsapp_number']
    user = data_manager.add_user(name=name, whatsapp_number=whatsapp_number, avatar_id=avatar_id)
    flash('Profile created!' if user else 'Error creating profile', 'success' if user else 'error')
    return redirect(url_for('user_selection'))

@app.route('/select_user/<int:user_id>')
def select_user(user_id):
    """Log in the selected user."""
    user = User.query.get(user_id)
    if user: login_user(user)
    return redirect(url_for('movies'))

@app.route('/movies')
def movies():
    """Display the main movies page with various sections."""
    try:
        new_releases = data_manager.get_new_releases(limit=10)
        popular_movies = data_manager.get_popular_movies(limit=10)
        top_rated = data_manager.get_top_rated_movies(limit=10)
        recent_comments = data_manager.get_recent_commented_movies(limit=5)
        categories = data_manager.get_all_categories_with_movies()
        platforms = data_manager.get_all_platforms()
        
        # Add watched avatars to the lists
        new_releases = data_manager._add_watched_avatars_to_movies(new_releases)
        popular_movies = data_manager._add_watched_avatars_to_movies(popular_movies)
        top_rated = data_manager._add_watched_avatars_to_movies(top_rated)
        # Add avatars to movies within categories as well
        for category in categories:
            category['movies'] = data_manager._add_watched_avatars_to_movies(category.get('movies', []))
        # Note: recent_comments already contains movie dicts from favorites, maybe add avatars there too?
        # recent_comments = data_manager._add_watched_avatars_to_movies(recent_comments) # Consider if needed

        friends_favorites = []
        if current_user.is_authenticated:
            # Note: Friends functionality is currently disabled in db_manager
            friends_favorites = data_manager.get_friends_favorites(current_user.id, limit=10)
            
        # Remove detailed debug prints
        # if new_releases: print("[DEBUG] Sample New Release Movie Structure:", new_releases[0])
        # ... (other debug prints removed)
        
    except Exception as e:
        app.logger.error(f"Error loading movie lists for /movies: {str(e)}")
        # Provide empty lists on error to prevent crashes
        new_releases, popular_movies, top_rated, recent_comments = [], [], [], []
        friends_favorites, categories, platforms = [], [], []

    return render_template('movies.html',
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
    """Display details for a specific movie."""
    movie = data_manager.get_movie_data(movie_id)
    if not movie:
        flash('Movie not found', 'error')
        return redirect(url_for('movies'))
        
    # Get users who watched this movie
    watched_entries = UserFavorite.query.filter_by(movie_id=movie_id, watched=True).all()
    watched_users = []
    for entry in watched_entries:
        user = User.query.get(entry.user_id)
        if user:
            avatar = Avatar.query.get(user.avatar_id)
            watched_users.append({
                'id': user.id,
                'name': user.name,
                'avatar_url': avatar.profile_image_url if avatar else None, # Handle missing avatar
                'rating': entry.rating
            })
            
    # OMDB data is already included in movie via get_movie_data
    omdb_data = movie.get('omdb_data') 
    
    # Get comments for this movie
    comments = []
    try:
        # Fetch UserFavorite entries with comments for this movie
        # Eager load user and avatar info
        comment_entries = UserFavorite.query.options(
            joinedload(UserFavorite.user).joinedload(User.avatar)
        ).filter(
            UserFavorite.movie_id == movie_id,
            UserFavorite.comment.isnot(None)
        ).order_by(UserFavorite.created_at.desc() if hasattr(UserFavorite, 'created_at') else UserFavorite.user_id.desc()).all()

        for entry in comment_entries:
            if entry.user:
                 profile_avatar_url = entry.user.avatar.profile_image_url if entry.user.avatar else Avatar().profile_image_url
                 hero_avatar_url = entry.user.avatar.hero_image_url if entry.user.avatar else Avatar().hero_image_url
                 comments.append({
                     'movie': movie, # Pass the movie dict itself for context
                     'comment_text': entry.comment,
                     'comment_user_name': entry.user.name,
                     'comment_user_avatar_url': profile_avatar_url,
                     'comment_user_hero_avatar_url': hero_avatar_url
                 })
    except Exception as e:
        app.logger.error(f"Error fetching comments for movie {movie_id}: {e}")

    return render_template('movie_detail.html', 
                         movie=movie, 
                         watched_users=watched_users, 
                         omdb_data=omdb_data, 
                         comments=comments, # Pass comments to the template
                         current_user=current_user)

@app.route('/toggle_watchlist/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watchlist(movie_id):
    """AJAX endpoint to add/remove a movie from the watchlist."""
    # upsert_favorite needs to handle finding the existing state
    return data_manager.upsert_favorite(current_user.id, movie_id, watchlist=True)

@app.route('/toggle_watched/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watched(movie_id):
    """AJAX endpoint to mark a movie as watched/unwatched."""
    # upsert_favorite needs to handle finding the existing state
    return data_manager.upsert_favorite(current_user.id, movie_id, watched=True)

@app.route('/rate_movie', methods=['POST'])
@login_required
@ajax_route
def rate_movie():
    """AJAX endpoint to save a movie rating and comment."""
    movie_id = int(request.form['movie_id'])
    # Rating comes from the modal script, ensure it's sent
    rating = float(request.form.get('rating', 0)) # Default to 0 if not sent?
    comment = request.form.get('comment', '')
    # Ensure rating is within valid range if necessary (e.g., 0.5 to 5)
    # rating = max(0.5, min(5, rating)) if rating else None 
    return data_manager.upsert_favorite(current_user.id, movie_id, rating=rating, comment=comment)

@app.route('/profile')
@login_required
def profile():
    """Display the current user's profile (simplified)."""
    # This currently redirects to user_profile, consider a dedicated profile page
    return redirect(url_for('user_profile', user_id=current_user.id))

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('user_selection'))

@app.route('/search')
def search():
    """Handle movie search requests."""
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('movies'))
        
    results = []
    # Consider optimizing search (e.g., using SQL LIKE or a search index)
    all_movies = data_manager.get_all_movies() 
    for movie_summary in all_movies:
        # Search in movie name/title (case-insensitive)
        if query.lower() in movie_summary.get('name', '').lower():
            # Fetch full data only for matches
            details = data_manager.get_movie_data(movie_summary['id'])
            if details: # Ensure movie data was found
                 # OMDB data should be part of details now
                # details['omdb'] = omdb_manager.get_omdb_data(m['id']) or {} # Removed redundant fetch
                results.append(details)
                
    return render_template('search_results.html', query=query, results=results)

# Obsolete route? Consider removing if not used.
# @app.route('/users')
# def users():
#     ... (implementation omitted) ...

@app.route('/users/<int:user_id>')
@login_required
def user_profile(user_id):
    """Display a specific user's profile and movie lists."""
    user_data = data_manager.get_user_data(user_id)
    if not user_data:
        flash('User not found', 'error')
        return redirect(url_for('movies'))
        
    # Favorites list includes watched/watchlist status
    favorites = user_data.get('favorites', [])
    watched = [fav for fav in favorites if fav.get('watched')]
    watchlist = [fav for fav in favorites if fav.get('watchlist')]    
    comments = sorted([fav for fav in favorites if fav.get('comment')], 
                      key=lambda x: x.get('created_at', '0'), reverse=True) # Sort by date if available
    last_comments = comments[:3] # Get the 3 most recent

    return render_template(
        'user_movies.html',
        user=user_data, # Pass the whole user_data dict
        watched=watched,
        watchlist=watchlist,
        last_comments=last_comments
    )

# Routes for adding/updating/deleting movies from user lists (Consider security/permissions)
@app.route('/users/<int:user_id>/add_movie', methods=['GET','POST'])
@login_required # Ensure user is logged in
def add_movie(user_id):
    """Display form or handle adding a movie to a user's list."""
    # Add check: Is current_user authorized to modify this user_id's list?
    # if current_user.id != user_id: 
    #    flash('Unauthorized', 'error')
    #    return redirect(url_for('movies'))
        
    if request.method == 'POST':
        movie_id = int(request.form['movie_id'])
        watched = 'watched' in request.form
        watchlist = 'watchlist' in request.form # Add watchlist handling
        rating = float(request.form['rating']) if request.form.get('rating') else None
        comment = request.form.get('comment')
        # Use upsert to handle adding/updating
        success = data_manager.upsert_favorite(user_id, movie_id, watched=watched, watchlist=watchlist, rating=rating, comment=comment)
        flash('Saved' if success else 'Error saving', 'success' if success else 'error')
        return redirect(url_for('user_profile', user_id=user_id))
        
    # Prepare data for the GET request form
    user_data = data_manager.get_user_by_id(user_id)
    all_movies = data_manager.get_all_movies()
    return render_template('add_movie.html', user=user_data, movies=all_movies)

@app.route('/users/<int:user_id>/update_movie/<int:movie_id>', methods=['GET','POST'])
@login_required
def update_movie(user_id, movie_id):
    """Display form or handle updating a movie in a user's list."""
    # Add authorization check: if current_user.id != user_id: ...

    # Get existing favorite data
    fav = data_manager.get_user_favorite(user_id, movie_id) # Assumes get_user_favorite exists
    if not fav:
        flash('Movie not found in your lists','error')
        return redirect(url_for('user_profile', user_id=user_id))
        
    if request.method == 'POST':
        watched = 'watched' in request.form
        watchlist = 'watchlist' in request.form
        rating = float(request.form.get('rating')) if request.form.get('rating') else None
        comment = request.form.get('comment')
        success = data_manager.upsert_favorite(user_id, movie_id, watched=watched, watchlist=watchlist, rating=rating, comment=comment)
        flash('Updated' if success else 'Error updating', 'success' if success else 'error')
        return redirect(url_for('user_profile', user_id=user_id))
        
    # Pass existing data to the template for GET request
    movie_data = data_manager.get_movie_data(movie_id)
    return render_template('update_movie.html', user_id=user_id, movie=movie_data, favorite=fav)

@app.route('/users/<int:user_id>/delete_movie/<int:movie_id>', methods=['POST'])
@login_required
def delete_movie(user_id, movie_id):
    """Handle deleting a movie from a user's list."""
    # Add authorization check: if current_user.id != user_id: ...
    success = data_manager.remove_favorite(user_id, movie_id)
    flash('Removed' if success else 'Error removing', 'success' if success else 'error')
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/category/<int:category_id>')
def category_detail(category_id):
    """Display movies belonging to a specific category."""
    category_obj = Category.query.get(category_id)
    if not category_obj:
        flash('Category not found', 'error')
        return redirect(url_for('movies'))
        
    movies_in_category = data_manager.get_movies_by_category(category_id)
    category_data = category_obj.to_dict(include_relationships=False) # Don't need movies inside dict again
    category_data['movies'] = movies_in_category # Add movies separately
    
    return render_template('category_detail.html', category=category_data, current_user=current_user)

# Temporary test route removed
# @app.route('/test_movie_data/<int:movie_id>')
# def test_movie_data(movie_id):
#     # ... (implementation removed) ...

if __name__=='__main__':
    app.run(debug=True, port=5002)