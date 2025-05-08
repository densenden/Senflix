import os
import sys
import requests
from dotenv import load_dotenv
from .interface import db, MovieOMDB, Movie
from sqlalchemy.exc import SQLAlchemyError
import urllib.request
import ssl
from pathlib import Path
import logging
from functools import lru_cache
from typing import Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OMDBManager:
    """Handles interactions with the OMDB API."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager # Reference to the main data manager
        self.api_key = os.getenv('OMDB_API_KEY')
        if not self.api_key:
            logger.error("OMDB_API_KEY environment variable not set.")
            # Consider raising an error or handling this state
            # raise ValueError("OMDB_API_KEY environment variable not set")
            
        self.base_url = 'https://www.omdbapi.com/'
        # Ensure static/movies directory exists
        self.movies_dir = Path('static/movies')
        self.movies_dir.mkdir(parents=True, exist_ok=True)
        
        # Secure SSL context for downloading posters
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        except Exception as e:
            logger.error(f"Failed to create secure SSL context: {e}", exc_info=True)
            self.ssl_context = None # Fallback to default context if creation fails

    def save_poster(self, poster_url: str, movie_id: int, imdb_id: str) -> Optional[str]:
        """Download poster image from URL and save locally."""
        if not poster_url or poster_url == 'N/A' or not imdb_id:
            logger.warning(f"Skipping poster save for movie {movie_id}: Invalid URL ('{poster_url}') or missing IMDB ID ('{imdb_id}').")
            return None
            
        filename = f"{imdb_id}-omdb-poster.jpg"
        filepath = self.movies_dir / filename
        
        try:
            # Use requests instead of urllib for better SSL handling
            response = requests.get(poster_url, timeout=10, stream=True)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Check content type to ensure it's an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Content is not an image: {content_type} for URL {poster_url}")
                return None
                
            # Save the image to file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if filepath.exists() and filepath.stat().st_size > 0:
                logger.info(f"Poster saved successfully for movie {movie_id}: {filepath}")
                return filename
            else:
                logger.error(f"Failed to save poster for movie {movie_id}. File might be empty or not created.")
                if filepath.exists():
                    filepath.unlink()
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error saving poster for movie {movie_id} from {poster_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error saving poster for movie {movie_id}: {e}", exc_info=True)
            return None

    # Cache OMDB API responses based on title (consider using IMDB ID for more specific caching)
    @lru_cache(maxsize=200)
    def fetch_omdb_data_by_title(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Fetch movie data from OMDB API by title (and optionally year)."""
        if not self.api_key:
             logger.error("Cannot fetch OMDB data: API key not configured.")
             return None
             
        params = {
            'apikey': self.api_key,
            't': title,
            'plot': 'full' # Request full plot details
        }
        if year:
            params['y'] = str(year)
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            
            if data.get('Response') == 'False':
                # Log API errors (e.g., "Movie not found!") but return None
                logger.warning(f"OMDB API Error for title '{title}' ({year or 'any year'}): {data.get('Error')}")
                return None
                
            return data # Return the JSON data as a dictionary
            
        except requests.exceptions.Timeout:
             logger.error(f"Timeout fetching OMDB data for title '{title}'.")
             return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching OMDB data for title '{title}': {e}", exc_info=True)
            return None

    @lru_cache(maxsize=200)
    def fetch_omdb_data_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Fetch movie data from OMDB API by IMDB ID."""
        if not self.api_key:
             logger.error("Cannot fetch OMDB data: API key not configured.")
             return None
             
        params = {
            'apikey': self.api_key,
            'i': imdb_id,
            'plot': 'full' # Request full plot details
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            
            if data.get('Response') == 'False':
                # Log API errors (e.g., "Movie not found!") but return None
                logger.warning(f"OMDB API Error for IMDB ID '{imdb_id}': {data.get('Error')}")
                return None
                
            return data # Return the JSON data as a dictionary
            
        except requests.exceptions.Timeout:
             logger.error(f"Timeout fetching OMDB data for IMDB ID '{imdb_id}'.")
             return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching OMDB data for IMDB ID '{imdb_id}': {e}", exc_info=True)
            return None

    def get_or_fetch_omdb_data(self, movie_id: int) -> Optional[Dict]:
        """Get OMDB data from DB or fetch from API if missing."""
        # Check if data exists in DB first
        existing_omdb = MovieOMDB.query.get(movie_id)
        if existing_omdb:
            logger.info(f"Found existing OMDB data for movie {movie_id}.")
            return existing_omdb.to_dict()
        
        logger.info(f"No existing OMDB data for movie {movie_id}, attempting fetch.")
        movie = Movie.query.get(movie_id) # Get the base movie info
        if not movie:
            logger.error(f"Cannot fetch OMDB data: Movie with ID {movie_id} not found.")
            return None
            
        # Fetch data using title and year
        omdb_data_dict = self.fetch_omdb_data_by_title(movie.name, movie.year)
        
        if not omdb_data_dict:
            logger.warning(f"Failed to fetch OMDB data for movie {movie_id} ('{movie.name}').")
            return None
        
        # Prepare data for DB insertion
        db_data = {
            'id': movie_id,
            'imdb_id': omdb_data_dict.get('imdbID'),
            'title': omdb_data_dict.get('Title'),
            'year': omdb_data_dict.get('Year'),
            'rated': omdb_data_dict.get('Rated'),
            'released': omdb_data_dict.get('Released'),
            'runtime': omdb_data_dict.get('Runtime'),
            'genre': omdb_data_dict.get('Genre'),
            'director': omdb_data_dict.get('Director'),
            'writer': omdb_data_dict.get('Writer'),
            'actors': omdb_data_dict.get('Actors'),
            'plot': omdb_data_dict.get('Plot'),
            'language': omdb_data_dict.get('Language'),
            'country': omdb_data_dict.get('Country'),
            'awards': omdb_data_dict.get('Awards'),
            'imdb_rating': omdb_data_dict.get('imdbRating'),
            'rotten_tomatoes': next((r['Value'] for r in omdb_data_dict.get('Ratings', []) if r['Source'] == 'Rotten Tomatoes'), None),
            'metacritic': omdb_data_dict.get('Metascore'),
            'type': omdb_data_dict.get('Type'),
            'dvd': omdb_data_dict.get('DVD'),
            'box_office': omdb_data_dict.get('BoxOffice'),
            'production': omdb_data_dict.get('Production'),
            'website': omdb_data_dict.get('Website'),
            # Poster needs to be handled separately after saving
        }
        
        # Attempt to save the poster
        poster_url = omdb_data_dict.get('Poster')
        imdb_id_val = db_data.get('imdb_id')
        saved_filename = self.save_poster(poster_url, movie_id, imdb_id_val)
        db_data['poster_img'] = saved_filename # Add filename (or None) to data

        # Save the fetched data (including poster filename) to the DB
        if self.save_omdb_data_to_db(movie_id, db_data):
            logger.info(f"Successfully fetched and saved OMDB data for movie {movie_id}.")
            return db_data # Return the newly fetched and saved data
        else:
            logger.error(f"Failed to save fetched OMDB data for movie {movie_id}.")
            return None

    def save_omdb_data_to_db(self, movie_id: int, db_data: Dict) -> bool:
        """Save formatted OMDB data dictionary to the database."""
        try:
            # Check again if data was inserted concurrently
            existing_data = MovieOMDB.query.get(movie_id)
            if existing_data:
                logger.warning(f"OMDB data for movie {movie_id} already exists. Updating.")
                # Update existing record
                for key, value in db_data.items():
                    if hasattr(existing_data, key) and value is not None:
                        # Handle potential type mismatches (e.g., rating)
                        current_type = type(getattr(existing_data, key)).__name__
                        if current_type == 'float' and not isinstance(value, float):
                            try: value = float(value)
                            except (ValueError, TypeError): value = None 
                        if value is not None: # Check again after potential conversion
                            setattr(existing_data, key, value)
            else:
                # Create new record
                 # Handle potential type mismatches for new record
                if 'imdb_rating' in db_data and not isinstance(db_data['imdb_rating'], float):
                     try: db_data['imdb_rating'] = float(db_data['imdb_rating'])
                     except (ValueError, TypeError): db_data['imdb_rating'] = None
                     
                new_data = MovieOMDB(**db_data)
                db.session.add(new_data)

            db.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"DB Error saving OMDB data for movie {movie_id}: {e}", exc_info=True)
            db.session.rollback()
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving OMDB data for movie {movie_id}: {e}", exc_info=True)
            db.session.rollback()
            return False

    # --- Potentially deprecated/unused methods below ---
    
    # get_omdb_data seems less useful than get_or_fetch_omdb_data
    # def get_omdb_data(self, movie_id):
    #    ...

    # _format_omdb_data is likely unused if to_dict() in MovieOMDB handles formatting
    # def _format_omdb_data(self, omdb_data):
    #    ...

    # save_omdb_data is superseded by save_omdb_data_to_db which takes a dict
    # def save_omdb_data(self, movie_id, omdb_data):
    #    ... 