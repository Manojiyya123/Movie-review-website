from models import db, User, Movie
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime

def init_db(app):
    """Initialize the database with the Flask app context"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def seed_admin_user():
    """Seed an admin user if none exists"""
    with current_app.app_context():
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

# User operations
def create_user(username, email, password, is_admin=False):
    """Create a new user"""
    try:
        user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    except IntegrityError:
        db.session.rollback()
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    return User.query.get(user_id)

def get_user_by_username(username):
    """Get user by username"""
    return User.query.filter_by(username=username).first()

def get_all_users():
    """Get all users"""
    return User.query.order_by(User.username).all()

def update_user(user_id, **kwargs):
    """Update user details"""
    user = User.query.get(user_id)
    if user:
        for key, value in kwargs.items():
            if key == 'password':
                user.set_password(value)
            elif hasattr(user, key):
                setattr(user, key, value)
        db.session.commit()
        return True
    return False

def delete_user(user_id):
    """Delete a user"""
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

# Movie operations
def add_movie(title, director, year, genre, description, poster_path=None):
    """Add a new movie to the database"""
    try:
        movie = Movie(
            title=title,
            director=director,
            year=year,
            genre=genre,
            description=description,
            poster=poster_path,
            date_added=datetime.utcnow()
        )
        db.session.add(movie)
        db.session.commit()
        return movie
    except IntegrityError:
        db.session.rollback()
        return None

def get_all_movies():
    """Get all movies sorted by title"""
    return Movie.query.order_by(Movie.title).all()

def get_movie_by_id(movie_id):
    """Get movie by ID"""
    return Movie.query.get(movie_id)

def update_movie(movie_id, **kwargs):
    """Update movie details"""
    movie = Movie.query.get(movie_id)
    if movie:
        for key, value in kwargs.items():
            if hasattr(movie, key):
                setattr(movie, key, value)
        db.session.commit()
        return True
    return False

def delete_movie(movie_id):
    """Delete a movie"""
    movie = Movie.query.get(movie_id)
    if movie:
        db.session.delete(movie)
        db.session.commit()
        return True
    return False

def search_movies(query):
    """Search movies by title, director or genre"""
    if not query:
        return []
    search_term = f"%{query}%"
    return Movie.query.filter(
        (Movie.title.ilike(search_term)) |
        (Movie.director.ilike(search_term)) |
        (Movie.genre.ilike(search_term))
    ).all()