import os
from functools import wraps
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from datamanager.db_manager import SQLiteDataManager
from datamanager.interface import User, Avatar, Category, Movie, StreamingPlatform, UserFavorite, MovieOMDB
from datamanager.omdb_manager import OMDBManager
from sqlalchemy.orm import joinedload

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Improve URL handling for serverless environments like Vercel
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Database setup
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/senflix.sqlite'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
            return jsonify({'error': str(e)}), 400
    return wrapped

# --- Routes ---

@app.route('/')
def user_selection():
    """Display user selection screen."""
    users = User.query.all()
    available_avatars = Avatar.query.all()
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
        
        # Apply user status using the helper function
        new_releases = data_manager._add_watched_avatars_to_movies(new_releases)
        popular_movies = data_manager._add_watched_avatars_to_movies(popular_movies)
        top_rated = data_manager._add_watched_avatars_to_movies(top_rated)
        
        # Add status to movies within categories
        for category in categories:
            movies_with_avatars = data_manager._add_watched_avatars_to_movies(category.get('movies', []))
            category['movies'] = data_manager._add_watched_avatars_to_movies(movies_with_avatars)
            
        # Get REAL favorites (favorite=True) from users with same avatar
        same_avatar_favorites = []
        if current_user.is_authenticated:
            same_avatar_users = User.query.filter(
                User.avatar_id == current_user.avatar_id, 
                User.id != current_user.id
            ).all()
            
            favorite_movie_ids = set() # Keep track of added movie IDs to avoid duplicates in this section
            limit_per_section = 10 # Limit the number of movies shown in this section

            for user in same_avatar_users:
                if len(same_avatar_favorites) >= limit_per_section:
                    break # Stop fetching if we reached the limit

                # Fetch entries marked as FAVORITE by this user
                user_favorites = UserFavorite.query.filter_by(
                    user_id=user.id, 
                    favorite=True # Filter by the new favorite flag
                ).limit(limit_per_section - len(same_avatar_favorites)).all() # Limit query 
                
                for fav in user_favorites:
                    if fav.movie_id not in favorite_movie_ids:
                         # Use get_movie_data and apply status for the *current* user viewing the card
                        movie_data = data_manager.get_movie_data(fav.movie_id)
                        if movie_data:
                            # Apply status for the logged-in user to the card
                            movie_with_status = data_manager._add_watched_avatars_to_movies([movie_data])[0] 
                            same_avatar_favorites.append({
                                'movie': movie_with_status, # Use movie with status flags for the viewer
                                'user': user, # User who favorited it (for potential future use, not shown on card)
                                'rating': fav.rating, # Rating by the other user (not shown on card)
                                'comment': fav.comment # Comment by the other user (not shown on card)
                            })
                            favorite_movie_ids.add(fav.movie_id)
                            if len(same_avatar_favorites) >= limit_per_section:
                                break # Stop inner loop if limit reached
            
    except Exception as e:
        app.logger.error(f"Error loading movie lists for /movies: {str(e)}")
        # Provide empty lists on error to prevent crashes
        new_releases, popular_movies, top_rated, recent_comments = [], [], [], []
        same_avatar_favorites, categories, platforms = [], [], []

    # Get most loved movies (based on favorite count)
    most_loved_movies = []
    # ... (existing most_loved_movies fetching) ...

    return render_template('movies.html',
                         new_releases=new_releases,
                         popular_movies=popular_movies,
                         same_avatar_favorites=same_avatar_favorites,
                         top_rated=top_rated,
                         most_loved_movies=most_loved_movies, 
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
                'avatar_url': avatar.profile_image_url if avatar else None, # simple Handle missing avatar
                'rating': entry.rating
            })
            
    # OMDB data is already included in movie via get_movie_data
    omdb_data = movie.get('omdb_data') 
    
    # Calculate average user rating
    avg_user_rating = data_manager.get_avg_movie_rating(movie_id)
    
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
                     'comment_user_id': entry.user.id,
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
                         avg_user_rating=avg_user_rating, # Pass average user rating
                         current_user=current_user)

@app.route('/toggle_watchlist/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watchlist(movie_id):
    """AJAX endpoint to add/remove a movie from the watchlist."""
    # Use toggle_user_favorite_attribute which handles the state toggle properly
    return data_manager.toggle_user_favorite_attribute(current_user.id, movie_id, 'watchlist')

@app.route('/toggle_watched/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_watched(movie_id):
    """AJAX endpoint to mark a movie as watched/unwatched."""
    # Use toggle_user_favorite_attribute which handles the state toggle properly
    return data_manager.toggle_user_favorite_attribute(current_user.id, movie_id, 'watched')

@app.route('/toggle_favorite/<int:movie_id>', methods=['POST'])
@login_required
@ajax_route
def toggle_favorite(movie_id):
    """AJAX endpoint to add/remove a movie from favorites."""
    # Use toggle_user_favorite_attribute which handles the state toggle properly
    return data_manager.toggle_user_favorite_attribute(current_user.id, movie_id, 'favorite')

@app.route('/rate_movie', methods=['POST'])
@login_required
@ajax_route
def rate_movie():
    """AJAX endpoint to save a movie rating and comment."""
    try:
        movie_id = int(request.form['movie_id'])
        # Rating comes from the modal script, ensure it's sent and valid
        rating_str = request.form.get('rating', '0')
        try:
            rating = float(rating_str) if rating_str.strip() else 0
        except ValueError:
            app.logger.warning(f"Invalid rating value: {rating_str}")
            rating = 0
            
        comment = request.form.get('comment', '')
        
        app.logger.info(f"Processing rating request: movie_id={movie_id}, rating={rating}, comment={comment}")
        
        # When a user rates a movie, we also implicitly mark it as watched
        result = data_manager.upsert_favorite(
            user_id=current_user.id, 
            movie_id=movie_id, 
            rating=rating, 
            comment=comment,
            watched=True  # Implicitly mark as watched when rating
        )
        
        if not result:
            app.logger.error(f"Error saving rating for movie {movie_id} by user {current_user.id}")
            return {'success': False, 'error': 'Error saving rating'}
            
        # Get the updated user favorite data to return to the client
        updated_favorite = data_manager.get_user_favorite(current_user.id, movie_id)
        app.logger.info(f"Rating saved successfully: {updated_favorite}")
        
        return {
            'success': True,
            'rating': updated_favorite.get('rating'),
            'comment': updated_favorite.get('comment', ''),
            'favorite': updated_favorite.get('favorite', False),
            'watched': updated_favorite.get('watched', False),
            'watchlist': updated_favorite.get('watchlist', False)
        }
    except KeyError as e:
        app.logger.error(f"Missing form fields for rating: {e}")
        return {'success': False, 'error': f'Missing data: {str(e)}'}, 400
    except ValueError as e:
        app.logger.error(f"Invalid data format for rating: {e}")
        return {'success': False, 'error': f'Invalid data format: {str(e)}'}, 400
    except Exception as e:
        app.logger.error(f"Unexpected error during movie rating: {e}", exc_info=True)
        return {'success': False, 'error': 'An unexpected error occurred'}, 500

@app.route('/get_movie_rating/<int:movie_id>', methods=['GET'])
@login_required
@ajax_route
def get_movie_rating(movie_id):
    """AJAX endpoint to get a user's rating and comment for a movie."""
    app.logger.info(f"=================== GET_MOVIE_RATING DEBUG ===================")
    app.logger.info(f"BEGIN get_movie_rating - movie_id: {movie_id}, user_id: {current_user.id}")
    
    # Add debug info about current user
    app.logger.info(f"Current user: {current_user.id}, {current_user.name}")
    
    try:
        # Use direct database query for better reliability
        user_favorite = UserFavorite.query.get((current_user.id, movie_id))
        
        if user_favorite:
            app.logger.info(f"Found UserFavorite: user_id={user_favorite.user_id}, movie_id={user_favorite.movie_id}")
            app.logger.info(f"Rating: {user_favorite.rating}, Comment: '{user_favorite.comment}'")
            app.logger.info(f"Watched: {user_favorite.watched}, Watchlist: {user_favorite.watchlist}, Favorite: {user_favorite.favorite}")
            
            # Return the data directly from the UserFavorite object if found
            response_data = {
                'success': True,
                'rating': user_favorite.rating,
                'comment': user_favorite.comment or '',  # Convert None to empty string for consistency
                'favorite': user_favorite.favorite,
                'watched': user_favorite.watched,
                'watchlist': user_favorite.watchlist
            }
            app.logger.info(f"Returning user favorite data: {response_data}")
            app.logger.info(f"=================== END GET_MOVIE_RATING DEBUG ===================")
            return response_data
        else:
            app.logger.info(f"No UserFavorite found for user {current_user.id} and movie {movie_id}")
            
            # Return a proper response when no data exists
            response_data = {
                'success': False,
                'rating': None,
                'comment': '',
                'favorite': False,
                'watched': False,
                'watchlist': False
            }
            app.logger.info(f"Returning default empty data: {response_data}")
            app.logger.info(f"=================== END GET_MOVIE_RATING DEBUG ===================")
            return response_data
            
    except Exception as e:
        app.logger.error(f"Error in get_movie_rating: {str(e)}", exc_info=True)
        app.logger.error(f"=================== END GET_MOVIE_RATING DEBUG ===================")
        
        # Return an error response
        return {
            'success': False,
            'error': str(e),
            'rating': None,
            'comment': '',
            'favorite': False,
            'watched': False,
            'watchlist': False
        }

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

@app.route('/search_omdb', methods=['GET'])
@login_required
def search_omdb():
    """Handle movie search requests against OMDB API."""
    query = request.args.get('q', '').strip()
    year = request.args.get('year')
    
    if not query:
        return jsonify({'results': []})
    
    app.logger.info(f"OMDB search: query='{query}', year='{year}'")
    
    # First, search in our own database
    results = []
    all_movies = data_manager.get_all_movies()
    for movie_summary in all_movies:
        if query.lower() in movie_summary.get('name', '').lower():
            # Fetch full data only for matches
            details = data_manager.get_movie_data(movie_summary['id'])
            if details:
                # Get OMDB data if available
                omdb_data = details.get('omdb_data') or {}
                poster_img = omdb_data.get('poster_img')
                default_poster = 'no-poster.jpg'
                poster_path = f"movies/{poster_img}" if poster_img else f"movies/{default_poster}"
                
                movie_data = {
                    'id': details.get('id'),
                    'title': details.get('name'),
                    'year': details.get('year'),
                    'source': 'senflix',
                    'plot': omdb_data.get('plot', ''),
                    'director': omdb_data.get('director', ''),
                    'actors': omdb_data.get('actors', ''),
                    'imdbID': omdb_data.get('imdb_id', ''),
                    'poster': url_for('static', filename=poster_path)
                }
                results.append(movie_data)
    
    # Try to get data from OMDB API if we have less than 5 results
    if len(results) < 5:
        try:
            # First try single movie search
            omdb_data = omdb_manager.fetch_omdb_data_by_title(query, int(year) if year and year.isdigit() else None)
            
            if omdb_data and omdb_data.get('Response') != 'False':
                # It's a single movie result
                movie_data = {
                    'title': omdb_data.get('Title', ''),
                    'year': omdb_data.get('Year', ''),
                    'imdbID': omdb_data.get('imdbID', ''),
                    'type': omdb_data.get('Type', ''),
                    'poster': omdb_data.get('Poster', ''),
                    'source': 'omdb',
                    'plot': omdb_data.get('Plot', ''),
                    'actors': omdb_data.get('Actors', ''),
                    'director': omdb_data.get('Director', ''),
                    'full_data': omdb_data
                }
                
                # Check if this movie is already in our results (by IMDB ID)
                if not any(r.get('imdbID') == movie_data['imdbID'] for r in results if 'imdbID' in r):
                    results.append(movie_data)
            
            # If still not enough results, try search endpoint (s parameter)
            if len(results) < 3:
                try:
                    app.logger.info(f"Trying OMDB search API for '{query}'")
                    # Construct URL for OMDB search API
                    api_key = os.getenv('OMDB_API_KEY')
                    search_url = f"https://www.omdbapi.com/?apikey={api_key}&s={query}"
                    if year and year.isdigit():
                        search_url += f"&y={year}"
                    
                    import requests
                    search_response = requests.get(search_url, timeout=5)
                    search_data = search_response.json()
                    
                    if search_data.get('Response') == 'True' and search_data.get('Search'):
                        app.logger.info(f"OMDB search returned {len(search_data['Search'])} results")
                        
                        for movie in search_data['Search'][:5]:  # Limit to 5 results
                            # Skip if already in results
                            if any(r.get('imdbID') == movie.get('imdbID') for r in results if 'imdbID' in r):
                                continue
                                
                            # Add to results
                            movie_data = {
                                'title': movie.get('Title', ''),
                                'year': movie.get('Year', ''),
                                'imdbID': movie.get('imdbID', ''),
                                'type': movie.get('Type', ''),
                                'poster': movie.get('Poster', ''),
                                'source': 'omdb',
                                # These fields won't be available from search but needed for consistency
                                'plot': '', 
                                'actors': '',
                                'director': ''
                            }
                            results.append(movie_data)
                except Exception as e:
                    app.logger.error(f"Error using OMDB search API: {e}")
        except Exception as e:
            app.logger.error(f"Error searching OMDB API: {e}")
    
    app.logger.info(f"Returning {len(results)} search results")
    return jsonify({'results': results})

@app.route('/add_new_movie', methods=['POST'])
@login_required
def add_new_movie():
    """Handle adding a new movie from the modal."""
    try:
        app.logger.info("Starting add_new_movie process")
        data = request.json
        
        if not data:
            app.logger.error("No data provided in request")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        app.logger.info(f"Received movie data: {data}")
        
        # Basic validation
        if not data.get('title'):
            app.logger.error("Movie title is required")
            return jsonify({'success': False, 'error': 'Movie title is required'}), 400
        
        # Create minimal movie data for Senflix database
        movie_data = {
            'name': data.get('title'),
            'year': data.get('year'),
            'director': data.get('director', '')
        }
        
        app.logger.info(f"Prepared movie data for database: {movie_data}")
        
        # Check if movie already exists by IMDB ID in MovieOMDB table
        existing_movie = None
        if data.get('imdbID'):
            existing_omdb = MovieOMDB.query.filter_by(imdb_id=data.get('imdbID')).first()
            if existing_omdb:
                existing_movie = Movie.query.get(existing_omdb.id)
                app.logger.info(f"Movie already exists with ID: {existing_movie.id}")
        
        # If not found by IMDB ID, also try searching by name and year
        if not existing_movie and data.get('title') and data.get('year'):
            existing_movie = Movie.query.filter_by(
                name=data.get('title'),
                year=data.get('year')
            ).first()
            if existing_movie:
                app.logger.info(f"Movie found by name and year with ID: {existing_movie.id}")
        
        if existing_movie:
            movie_id = existing_movie.id
            new_movie = {'id': movie_id}
        else:
            # Add the movie to the database
            app.logger.info("Adding new movie to database")
            new_movie = data_manager.add_movie(movie_data)
            
            if not new_movie:
                app.logger.error("Failed to add movie to database")
                return jsonify({'success': False, 'error': 'Failed to add movie to database'}), 500
            
            movie_id = new_movie.get('id')
            app.logger.info(f"New movie added with ID: {movie_id}")
        
        # Process OMDB data and save poster
        poster_filename = None
        if data.get('source') == 'omdb' and data.get('imdbID'):
            app.logger.info(f"Processing OMDB data for movie {movie_id}")
            
            try:
                # If we have a poster URL, save the poster
                poster_url = data.get('poster')
                imdb_id = data.get('imdbID')
                
                if poster_url and poster_url != 'N/A' and imdb_id:
                    app.logger.info(f"Saving poster from URL: {poster_url}")
                    poster_filename = omdb_manager.save_poster(poster_url, movie_id, imdb_id)
                    app.logger.info(f"Poster saved as: {poster_filename or 'None'}")
                
                # Try to get full data from OMDB API if we have an IMDB ID
                try:
                    if data.get('imdbID'):
                        # First try to fetch directly by IMDB ID for more accurate results
                        imdb_id = data.get('imdbID')
                        omdb_direct_data = omdb_manager.fetch_omdb_data_by_imdb_id(imdb_id)
                        
                        if omdb_direct_data:
                            # If we got data directly by IMDB ID, convert to our DB format
                            complete_data = {
                                'id': movie_id,
                                'imdb_id': omdb_direct_data.get('imdbID'),
                                'title': omdb_direct_data.get('Title'),
                                'year': omdb_direct_data.get('Year'),
                                'rated': omdb_direct_data.get('Rated'),
                                'released': omdb_direct_data.get('Released'),
                                'runtime': omdb_direct_data.get('Runtime'),
                                'genre': omdb_direct_data.get('Genre'),
                                'director': omdb_direct_data.get('Director'),
                                'writer': omdb_direct_data.get('Writer'),
                                'actors': omdb_direct_data.get('Actors'),
                                'plot': omdb_direct_data.get('Plot'),
                                'language': omdb_direct_data.get('Language'),
                                'country': omdb_direct_data.get('Country'),
                                'awards': omdb_direct_data.get('Awards'),
                                'imdb_rating': omdb_direct_data.get('imdbRating'),
                                'rotten_tomatoes': next((r['Value'] for r in omdb_direct_data.get('Ratings', []) if r['Source'] == 'Rotten Tomatoes'), None),
                                'metacritic': omdb_direct_data.get('Metascore'),
                                'type': omdb_direct_data.get('Type'),
                                'dvd': omdb_direct_data.get('DVD'),
                                'box_office': omdb_direct_data.get('BoxOffice'),
                                'production': omdb_direct_data.get('Production'),
                                'website': omdb_direct_data.get('Website'),
                                'poster_img': poster_filename # Use saved poster filename
                            }
                            
                            # Save the complete data
                            if omdb_manager.save_omdb_data_to_db(movie_id, complete_data):
                                app.logger.info(f"Saved complete OMDB data from direct API fetch with poster: {poster_filename}")
                            else:
                                app.logger.error(f"Failed to save complete OMDB data to database")
                        else:
                            # Fall back to the existing method
                            complete_omdb_data = omdb_manager.get_or_fetch_omdb_data(movie_id)
                            app.logger.info(f"Retrieved complete OMDB data via get_or_fetch_omdb_data: {complete_omdb_data is not None}")
                            
                            # If we have a poster that wasn't saved by get_or_fetch_omdb_data, update it
                            if complete_omdb_data and poster_filename and 'poster_img' not in complete_omdb_data:
                                try:
                                    omdb_obj = MovieOMDB.query.get(movie_id)
                                    if omdb_obj:
                                        omdb_obj.poster_img = poster_filename
                                        db.session.commit()
                                        app.logger.info(f"Updated poster_img for movie {movie_id} to {poster_filename}")
                                except Exception as e:
                                    app.logger.error(f"Error updating poster_img: {e}")
                    else:
                        # If no IMDB ID, use the existing method
                        complete_omdb_data = omdb_manager.get_or_fetch_omdb_data(movie_id)
                        app.logger.info(f"Retrieved complete OMDB data: {complete_omdb_data is not None}")
                except Exception as omdb_error:
                    app.logger.error(f"Error fetching complete OMDB data: {omdb_error}")
            except Exception as e:
                app.logger.error(f"Error processing OMDB data: {e}", exc_info=True)
        
        # Add movie to user's collections based on selections
        user_id = current_user.id
        
        # Update user preferences
        watched = data.get('watched', False)
        watchlist = data.get('watchlist', False)
        favorite = data.get('favorite', False)
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        app.logger.info(f"Updating user preferences: user_id={user_id}, movie_id={movie_id}, watched={watched}, watchlist={watchlist}, favorite={favorite}, rating={rating}")
        
        # Update user's movie preferences
        result = data_manager.upsert_favorite(
            user_id=user_id,
            movie_id=movie_id,
            rating=rating,
            comment=comment,
            watched=watched,
            watchlist=watchlist,
            favorite=favorite
        )
        
        if not result:
            app.logger.error(f"Failed to update user preferences for movie {movie_id}")
            return jsonify({'success': False, 'error': 'Failed to update user preferences'}), 500
        
        # Save categories if provided
        if data.get('categories'):
            app.logger.info(f"Saving categories for movie {movie_id}: {data.get('categories')}")
            
            # Get all categories to add at once 
            categories_to_add = []
            for category_id in data.get('categories'):
                try:
                    # Get category
                    category = Category.query.get(int(category_id))
                    if category:
                        categories_to_add.append(category)
                    else:
                        app.logger.warning(f"Category {category_id} not found when adding movie {movie_id}")
                except Exception as e:
                    app.logger.error(f"Error finding category {category_id}: {e}")
            
            # If we have categories to add
            if categories_to_add:
                try:
                    # Get the movie once
                    movie = Movie.query.get(movie_id)
                    if movie:
                        # Use the SQL association table directly instead of the relationship
                        from datamanager.interface import db, movie_categories
                        
                        # Add movie-category associations
                        for category in categories_to_add:
                            # Check if association already exists
                            exists = db.session.query(movie_categories).filter_by(
                                movie_id=movie_id,
                                category_id=category.id
                            ).first()
                            
                            if not exists:
                                # Insert into the association table
                                db.session.execute(movie_categories.insert().values(
                                    movie_id=movie_id,
                                    category_id=category.id
                                ))
                        
                        # Commit all changes at once
                        db.session.commit()
                        app.logger.info(f"Added movie {movie_id} to {len(categories_to_add)} categories")
                    else:
                        app.logger.warning(f"Movie {movie_id} not found when adding categories")
                except Exception as e:
                    app.logger.error(f"Error saving categories for movie {movie_id}: {e}", exc_info=True)
                    db.session.rollback()
        
        app.logger.info(f"Movie {movie_id} added successfully")
        return jsonify({
            'success': True,
            'movie_id': movie_id,
            'poster_filename': poster_filename
        })
        
    except Exception as e:
        app.logger.error(f"Error adding new movie: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """API endpoint to get all categories."""
    try:
        categories = data_manager.get_all_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        app.logger.error(f"Error getting categories: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Obsolete route? Consider removing if not used.
@app.route('/users')
def users():
    """Display all users grouped by their avatars."""
    try:
        # Get all users with their avatars
        users = User.query.options(joinedload(User.avatar)).all()
        
        # Group users by avatar
        avatar_groups = {}
        for user in users:
            avatar_name = user.avatar.name if user.avatar else 'Default'
            if avatar_name not in avatar_groups:
                avatar_groups[avatar_name] = {
                    'name': avatar_name,
                    'users': []
                }
            avatar_groups[avatar_name]['users'].append(user)
        
        # Convert to list for template
        avatar_groups = list(avatar_groups.values())
        
        return render_template('users.html', 
                             avatar_groups=avatar_groups,
                             current_user=current_user)
    except Exception as e:
        app.logger.error(f"Error in users route: {e}")
        return redirect(url_for('movies'))

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
    
    # Ensure each favorite has the movie data
    for fav in favorites:
        if isinstance(fav, dict) and 'movie' not in fav:
            movie_data = data_manager.get_movie_data(fav.get('movie_id'))
            if movie_data:
                fav.update(movie_data)
    
    watched = [fav for fav in favorites if fav.get('watched')]
    watchlist = [fav for fav in favorites if fav.get('watchlist')]    
    favorite_movies = [fav for fav in favorites if fav.get('favorite')]
    comments = sorted([fav for fav in favorites if fav.get('comment')], 
                      key=lambda x: x.get('created_at', '0'), reverse=True) # Sort by date if available
    last_comments = comments[:3] # Get the 3 most recent

    return render_template(
        'user_movies.html',
        user=user_data, # Pass the whole user_data dict
        watched=watched,
        watchlist=watchlist,
        favorites=favorite_movies,
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

@app.route('/blockbuster')
def blockbuster():
    """Display all blockbuster/popular movies."""
    # Get all movies without limit
    popular_movies = data_manager.get_popular_movies(limit=None)
    # Sort by number of favorites if available
    popular_movies = sorted(popular_movies, key=lambda x: len(x.get('favorites', [])) if x.get('favorites') else 0, reverse=True)
    popular_movies = data_manager._add_watched_avatars_to_movies(popular_movies)
    return render_template('blockbuster.html', movies=popular_movies, current_user=current_user)

@app.route('/top-rated')
def top_rated():
    """Display all top rated movies."""
    top_rated_movies = data_manager.get_top_rated_movies(limit=None)  # No limit here to get all movies
    top_rated_movies = data_manager._add_watched_avatars_to_movies(top_rated_movies)
    return render_template('top_rated.html', movies=top_rated_movies, current_user=current_user)

@app.route('/community-comments')
def community_comments():
    """Display all community comments."""
    recent_comments = data_manager.get_recent_commented_movies(limit=None)  # Remove limit to get all comments
    return render_template('community_comments.html', comments=recent_comments, current_user=current_user)

@app.route('/avatar/<int:avatar_id>')
def avatar_detail(avatar_id):
    """Display details for a specific avatar."""
    try:
        # Get avatar details
        avatar = Avatar.query.get(avatar_id)
        if not avatar:
            flash('Avatar not found', 'error')
            return redirect(url_for('movies'))

        # Get users with this avatar
        users = User.query.filter_by(avatar_id=avatar_id).all()
        app.logger.info(f"Found {len(users)} users with avatar_id={avatar_id}")

        # Get favorites from users with this avatar
        favorites = []
        favorite_movie_ids = set()  # To avoid duplicates
        limit_per_section = 10

        # Also collect all movie IDs favorited by users with this avatar for category analysis
        all_favorite_movie_ids = set()

        for user in users:
            app.logger.info(f"Processing favorites for user_id={user.id}")
            if len(favorites) >= limit_per_section:
                break

            user_favorites = UserFavorite.query.filter_by(
                user_id=user.id,
                favorite=True
            ).all()  # Get all for category counting, but limit display
            
            app.logger.info(f"User {user.id} has {len(user_favorites)} favorites")

            for fav in user_favorites:
                # Add to the complete set for category analysis
                all_favorite_movie_ids.add(fav.movie_id)
                
                # Add to display list if under limit
                if len(favorites) < limit_per_section and fav.movie_id not in favorite_movie_ids:
                    movie_data = data_manager.get_movie_data(fav.movie_id)
                    if movie_data:
                        movie_with_status = data_manager._add_watched_avatars_to_movies([movie_data])[0]
                        favorites.append({
                            'movie': movie_with_status,
                            'user': user,
                            'rating': fav.rating,
                            'comment': fav.comment
                        })
                        favorite_movie_ids.add(fav.movie_id)
                        if len(favorites) >= limit_per_section:
                            break

        app.logger.info(f"Collected {len(all_favorite_movie_ids)} unique favorite movie IDs")

        # Get all movie categories for the favorited movies
        popular_categories = []
        category_counts = {}
        
        try:
            # First method: Query directly using SQLAlchemy relationships
            if all_favorite_movie_ids:
                # Get all movies with their categories
                favorite_movies = Movie.query.filter(Movie.id.in_(all_favorite_movie_ids)).options(
                    joinedload(Movie.categories)
                ).all()
                
                # Count categories and track category objects for their IDs and images
                category_objects = {}
                
                # Count categories
                for movie in favorite_movies:
                    for category in movie.categories:
                        if category.name in category_counts:
                            category_counts[category.name] += 1
                        else:
                            category_counts[category.name] = 1
                            
                        # Store the category object for later use
                        category_objects[category.name] = category
                
                # Also check direct category relationship
                for movie in favorite_movies:
                    if movie.category:
                        if movie.category.name in category_counts:
                            category_counts[movie.category.name] += 1
                        else:
                            category_counts[movie.category.name] = 1
                            
                        # Store the category object for later use
                        category_objects[movie.category.name] = movie.category
                
                app.logger.info(f"Collected {len(category_counts)} categories from favorite movies")
                
                # Convert to list of dicts and sort by count
                popular_categories = [
                    {
                        'name': name,
                        'count': count,
                        'id': category_objects[name].id,
                        'img': category_objects[name].img
                    }
                    for name, count in category_counts.items()
                ]
                popular_categories.sort(key=lambda x: x['count'], reverse=True)
                
                # Limit to top 8
                popular_categories = popular_categories[:8]
            
            # If no results from first method, try the SQL method
            if not popular_categories and all_favorite_movie_ids:
                app.logger.info("Using SQL query method for categories")
                # Query to get category counts from favorites of users with this avatar
                category_counts = db.session.query(
                    Category.name,
                    Category.id,
                    Category.img,
                    db.func.count(movie_categories.c.movie_id).label('count')
                ).join(
                    movie_categories,
                    Category.id == movie_categories.c.category_id
                ).join(
                    Movie,
                    Movie.id == movie_categories.c.movie_id
                ).filter(
                    Movie.id.in_(all_favorite_movie_ids)
                ).group_by(
                    Category.name,
                    Category.id,
                    Category.img
                ).order_by(
                    db.desc('count')
                ).limit(8).all()

                popular_categories = [
                    {
                        'name': name,
                        'id': id,
                        'img': img,
                        'count': count
                    }
                    for name, id, img, count in category_counts
                ]
                
                app.logger.info(f"SQL query returned {len(popular_categories)} categories")
            
        except Exception as e:
            app.logger.error(f"Error fetching popular categories: {e}", exc_info=True)
            popular_categories = []

        app.logger.info(f"Final popular categories: {popular_categories}")

        return render_template('avatar_detail.html',
                             avatar=avatar,
                             users=users,
                             favorites=favorites,
                             popular_categories=popular_categories,
                             current_user=current_user)

    except Exception as e:
        app.logger.error(f"Error in avatar_detail route: {e}", exc_info=True)
        flash('Error loading avatar details', 'error')
        return redirect(url_for('movies'))

if __name__ == "__main__":
    # For development only
    # In production, use gunicorn or similar WSGI server
    app.run(host='0.0.0.0', port=5002)