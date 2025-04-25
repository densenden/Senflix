import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from flask import url_for
from app import app
from datamanager.interface import User, Avatar

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_user_selection_route_empty_db(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Who's watching?" in response.data
    # Should not error if no users
    assert b"New Profile" in response.data or b"Create New Profile" in response.data

def test_user_selection_route_with_users(client):
    # Create a test avatar and user directly in the DB
    with app.app_context():
        avatar = Avatar(name='TestAvatar', description='desc', profile_image='test.png', hero_image='hero.png')
        User.query.delete()
        Avatar.query.delete()
        from datamanager.interface import db
        db.session.add(avatar)
        db.session.commit()
        user = User(name='TestUser', whatsapp_number='+491234567', avatar_id=avatar.id)
        db.session.add(user)
        db.session.commit()
    response = client.get('/')
    assert response.status_code == 200
    assert b'TestUser' in response.data
    assert b'+491234567' in response.data
    assert b'TestAvatar' not in response.data  # Avatar name is not shown in card
    assert b"Who's watching?" in response.data
    # Clean up
    with app.app_context():
        User.query.delete()
        Avatar.query.delete()
        db.session.commit()
