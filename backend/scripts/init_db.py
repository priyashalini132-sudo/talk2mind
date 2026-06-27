import sys
import os

# Adjust path to find app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app.models import User
from app.auth import get_password_hash

def init_db():
    print("Initializing SQLite Database...")
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    
    # Seed a demo user
    db = SessionLocal()
    try:
        demo_username = "demo"
        demo_email = "demo@talk2mind.com"
        
        # Check if demo user already exists
        exists = db.query(User).filter(User.username == demo_username).first()
        if not exists:
            print("Seeding demo user account (username: 'demo', password: 'password123')...")
            demo_user = User(
                username=demo_username,
                email=demo_email,
                full_name="Demo User",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            db.add(demo_user)
            db.commit()
            print("Demo user seeded.")
        else:
            print("Demo user already exists.")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
