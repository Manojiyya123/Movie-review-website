from app import app
from database import create_user, get_user_by_username

# Admin user details
admin_username = "admin"
admin_email = "admin@example.com"
admin_password = "adminpassword"  # You can change this to a stronger password

# Create admin user with app context
with app.app_context():
    # Check if admin already exists
    existing_admin = get_user_by_username(admin_username)
    
    if existing_admin:
        print(f"Admin user '{admin_username}' already exists!")
    else:
        # Create the admin user using the existing function
        success = create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_admin=True
        )
        
        if success:
            print(f"Admin user created successfully!")
            print(f"Username: {admin_username}")
            print(f"Password: {admin_password}")
            print(f"Email: {admin_email}")
            print("You can now log in with these credentials.")
        else:
            print("Failed to create admin user. Check if username or email already exists.")