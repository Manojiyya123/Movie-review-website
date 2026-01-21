from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from models import User, Movie, UserPrivilegeLog, Review
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images/posters'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max file size

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create tables
with app.app_context():
    db.create_all()

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().timestamp()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        return f"images/posters/{unique_filename}"
    return None

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    movies = Movie.query.order_by(Movie.title).all()
    return render_template('index.html', movies=movies)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    
    if query:
        # Try to parse year if the query is a number
        try:
            year = int(query)
            movies = Movie.query.filter(Movie.year == year).all()
            if movies:
                return render_template('search.html', movies=movies, query=query)
        except ValueError:
            pass
        
        # Search across multiple fields
        movies = Movie.query.filter(
            db.or_(
                Movie.title.ilike(f'%{query}%'),
                Movie.director.ilike(f'%{query}%'),
                Movie.genre.ilike(f'%{query}%'),
                Movie.description.ilike(f'%{query}%')
            )
        ).order_by(Movie.title).all()
    else:
        # Show all movies if no query
        movies = Movie.query.order_by(Movie.title).all()
    
    return render_template('search.html', movies=movies, query=query)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    # Filter out admin reviews by joining with User table and checking is_admin status
    reviews = Review.query.join(User).filter(Review.movie_id == movie_id, User.is_admin == False).all()
    return render_template('movie_detail.html', movie=movie, reviews=reviews)

@app.route('/movie/<int:movie_id>/review', methods=['POST'])
@login_required
def add_movie_review(movie_id):
    content = request.form.get('content')
    rating = request.form.get('rating')
    
    if not content or not rating:
        flash('Please fill all fields', 'danger')
        return redirect(url_for('movie_detail', movie_id=movie_id))
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        flash('Rating must be between 1 and 5', 'danger')
        return redirect(url_for('movie_detail', movie_id=movie_id))
    
    review = Review(
        content=content,
        rating=rating,
        user_id=current_user.id,
        movie_id=movie_id,
        created_at=datetime.utcnow()
    )
    
    db.session.add(review)
    db.session.commit()
    flash('Review added successfully!', 'success')
    return redirect(url_for('movie_detail', movie_id=movie_id))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('Please fill all fields', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match!', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken!', 'danger')
        else:
            user = User(
                username=username,
                email=email,
                is_admin=False
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('auth/signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    
    movies = Movie.query.all()
    users = User.query.all()
    return render_template('admin/dashboard.html', movies=movies, users=users)

@app.route('/admin/movie/<int:movie_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_movie(movie_id):
    if not current_user.is_admin:
        abort(403)
    
    movie = Movie.query.get_or_404(movie_id)
    
    if request.method == 'POST':
        movie.title = request.form.get('title')
        movie.director = request.form.get('director')
        movie.year = request.form.get('year')
        movie.genre = request.form.get('genre')
        movie.description = request.form.get('description')
        
        # Handle file upload if a new poster was provided
        if 'poster' in request.files:
            file = request.files['poster']
            if file.filename != '':
                poster_path = save_uploaded_file(file)
                if poster_path:
                    movie.poster = poster_path
        
        db.session.commit()
        flash('Movie updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_movie.html', movie=movie)

@app.route('/admin/movie/add', methods=['GET', 'POST'])
@login_required
def admin_add_movie():
    if not current_user.is_admin:
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        director = request.form.get('director')
        year = request.form.get('year')
        genre = request.form.get('genre')
        description = request.form.get('description')
        
        if not all([title, director, year, genre, description]):
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('admin_add_movie'))
        
        try:
            year = int(year)
            if year < 1900 or year > datetime.now().year + 5:
                raise ValueError
        except ValueError:
            flash('Invalid year', 'danger')
            return redirect(url_for('admin_add_movie'))
        
        poster_path = save_uploaded_file(request.files.get('poster'))
        
        current_time = datetime.utcnow()
        movie = Movie(
            title=title,
            director=director,
            year=year,
            genre=genre,
            description=description,
            poster=poster_path,
            date_added=current_time
        )
        db.session.add(movie)
        db.session.commit()
        
        # Debug print
        print(f"Added movie {title} at {current_time}")
        
        flash('Movie added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_movie.html')

@app.route('/admin/movie/<int:movie_id>/delete', methods=['POST'])
@login_required
def admin_delete_movie(movie_id):
    if not current_user.is_admin:
        abort(403)
    
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Movie deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        flash('Cannot delete your own admin account!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/toggle-privilege', methods=['POST'])
@login_required
def admin_toggle_privilege(user_id):
    if not current_user.is_admin:
        abort(403)
    
    # Prevent admin from modifying their own account
    if user_id == current_user.id:
        flash('Cannot modify your own admin privileges!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Create a log entry before making the change
    log_entry = UserPrivilegeLog(
        user_id=user.id,
        modified_by=current_user.id,
        old_status=user.is_admin,
        new_status=not user.is_admin,
        timestamp=datetime.utcnow()
    )
    
    # Toggle admin status
    user.is_admin = not user.is_admin
    
    try:
        db.session.add(log_entry)
        db.session.commit()
        
        if user.is_admin:
            flash(f'Successfully granted admin privileges to {user.username}!', 'success')
        else:
            flash(f'Successfully removed admin privileges from {user.username}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating privileges.', 'danger')
        app.logger.error(f"Error updating privileges: {str(e)}")
    
    return redirect(url_for('admin_dashboard'))

# Error handlers
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Initialize database and create admin user
def initialize_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')  # Now this will work
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")

# Initialize the database
initialize_database()

@app.template_filter('avg')
def avg_filter(l):
    """Calculate the average of a list of numbers"""
    if not l:
        return 0
    return sum(l) / len(l)

if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    app.run(debug=True)