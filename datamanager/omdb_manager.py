import os
import sys
import requests
from dotenv import load_dotenv
from .interface import db, MovieOMDB, Movie
import urllib.request
import ssl
from pathlib import Path
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OMDBManager:
    """Manager for OMDB API interactions."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.api_key = os.getenv('OMDB_API_KEY')
        if not self.api_key:
            raise ValueError("OMDB_API_KEY environment variable not set")
            
        self.base_url = 'https://www.omdbapi.com/'
        self.movies_dir = Path('static/movies')
        self.movies_dir.mkdir(parents=True, exist_ok=True)
        
        # Create secure SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.check_hostname = True

    def save_poster(self, poster_url, movie_id, imdb_id):
        """Save movie poster to local storage"""
        logger.info(f"Starting poster save process for movie {movie_id}")
        
        if not poster_url or poster_url == 'N/A':
            logger.warning("No valid poster URL provided")
            return None
            
        try:
            filename = f"{imdb_id}-omdb-poster.jpg"
            filepath = self.movies_dir / filename
            
            if not self.movies_dir.exists():
                self.movies_dir.mkdir(parents=True, exist_ok=True)
            
            # Download with secure SSL context
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.ssl_context))
            urllib.request.install_opener(opener)
            
            urllib.request.urlretrieve(poster_url, filepath)
            
            if filepath.exists():
                logger.info(f"Poster saved successfully at: {filepath}")
                return filename
            else:
                logger.error("Failed to save poster file")
                return None
            
        except Exception as e:
            logger.error(f"Error saving poster: {str(e)}", exc_info=True)
            return None

    @lru_cache(maxsize=100)
    def fetch_omdb_data(self, title):
        """Fetch movie data from OMDB API with caching"""
        params = {
            'apikey': self.api_key,
            't': title,
            'plot': 'full'
        }
        
        try:
            response = requests.get(
                self.base_url, 
                params=params, 
                verify=True,  # Enable SSL verification
                timeout=10    # Add timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'False':
                logger.warning(f"API Error: {data.get('Error')}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {str(e)}", exc_info=True)
            return None

    def get_omdb_data(self, movie_id):
        """Get movie data from OMDB API."""
        movie = self.data_manager.get_movie_data(movie_id)
        if not movie:
            return None
            
        params = {
            'apikey': self.api_key,
            't': movie.title,
            'y': movie.year
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching OMDB data: {e}")
            return None

    def _format_omdb_data(self, omdb_data):
        """Format OMDB data for API response"""
        return {
            'title': omdb_data.title,
            'year': omdb_data.year,
            'rated': omdb_data.rated,
            'released': omdb_data.released,
            'runtime': omdb_data.runtime,
            'genre': omdb_data.genre,
            'director': omdb_data.director,
            'writer': omdb_data.writer,
            'actors': omdb_data.actors,
            'plot': omdb_data.plot,
            'language': omdb_data.language,
            'country': omdb_data.country,
            'awards': omdb_data.awards,
            'poster': omdb_data.poster_img,
            'imdb_rating': omdb_data.imdb_rating,
            'rotten_tomatoes': omdb_data.rotten_tomatoes,
            'metacritic': omdb_data.metacritic,
            'type': omdb_data.type,
            'dvd': omdb_data.dvd,
            'box_office': omdb_data.box_office,
            'production': omdb_data.production,
            'website': omdb_data.website
        }

    def save_omdb_data(self, movie_id, omdb_data):
        """Save OMDB data for a movie"""
        try:
            movie = Movie.query.get(movie_id)
            if not movie:
                logger.error(f"Movie with ID {movie_id} not found")
                return False

            existing_data = MovieOMDB.query.filter_by(id=movie_id).first()
            
            if existing_data:
                for key, value in omdb_data.items():
                    if hasattr(existing_data, key):
                        if key == 'poster_img' and value:
                            setattr(existing_data, key, value)
                        elif key != 'poster_img' and value is not None:
                            setattr(existing_data, key, value)
            else:
                new_data = MovieOMDB(**omdb_data)
                db.session.add(new_data)

            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving OMDB data: {str(e)}", exc_info=True)
            db.session.rollback()
            return False 