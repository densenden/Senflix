from app import app

def test_static_url():
    """Test that static URL generation works correctly."""
    with app.test_request_context():
        url = app.url_for('static', filename='movies/tt0062622-omdb-poster.jpg')
        assert url.startswith('/static/')
        assert 'movies/tt0062622-omdb-poster.jpg' in url 