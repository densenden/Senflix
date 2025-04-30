from flask import Flask
app = Flask(__name__)
with app.test_request_context():
    print(app.url_for('static', filename='movies/tt0062622-omdb-poster.jpg')) 