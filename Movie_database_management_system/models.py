from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reviews = db.relationship('Review', backref='user', lazy=True)
    privilege_logs = db.relationship('UserPrivilegeLog', foreign_keys='UserPrivilegeLog.user_id', backref='user')
    privilege_changes = db.relationship('UserPrivilegeLog', foreign_keys='UserPrivilegeLog.modified_by', backref='modifier')
    
    def set_password(self, password):
        """Create hashed password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    __tablename__ = 'movies'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    director = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    poster = db.Column(db.String(200))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='movie', lazy=True)

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)

class UserPrivilegeLog(db.Model):
    """Log for tracking admin privilege changes"""
    __tablename__ = 'user_privilege_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    modified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    old_status = db.Column(db.Boolean, nullable=False)
    new_status = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PrivilegeLog {self.user_id} {self.old_status}->{self.new_status}>'

# Database Triggers (implemented as SQLAlchemy events)
from sqlalchemy import event

@event.listens_for(UserPrivilegeLog, 'after_insert')
def log_privilege_change(mapper, connection, target):
    """Trigger to log privilege changes"""
    # Log the change to a separate audit table if needed
    pass

@event.listens_for(User, 'before_update')
def prevent_last_admin_removal(mapper, connection, target):
    """Prevent removal of admin privileges from the last admin"""
    if hasattr(target, '_sa_instance_state') and \
       'is_admin' in target._sa_instance_state.committed_state and \
       not target.is_admin:
        # Check if this is the last admin
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            raise ValueError("Cannot remove admin privileges from the last admin user.")