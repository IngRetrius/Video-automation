"""
Script to reset database
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from news_scraper.config.database import engine, Base, init_db

def reset_database():
    """Drop all tables and recreate them"""
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✓ Existing tables dropped")
        
        # Recreate tables
        init_db()
        print("✓ Database reset complete")
    except Exception as e:
        print(f"✗ Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()