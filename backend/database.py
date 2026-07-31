from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings


engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations():
    """
    Ensures existing database schemas are up to date for backwards compatibility.
    Applies missing columns like 'image_type' to 'manual_images' if running on an existing DB.
    """
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "manual_images" in tables:
            columns = [c["name"] for c in inspector.get_columns("manual_images")]
            
            with engine.connect() as conn:
                # Add image_type column if it doesn't exist
                if "image_type" not in columns:
                    print("Migration: Adding 'image_type' column to 'manual_images' table...")
                    conn.execute(text("ALTER TABLE manual_images ADD COLUMN image_type VARCHAR(50) DEFAULT 'extracted';"))
                    conn.commit()
                
                # Ensure timestamp is nullable
                if "timestamp" in columns:
                    try:
                        conn.execute(text("ALTER TABLE manual_images ALTER COLUMN timestamp DROP NOT NULL;"))
                        conn.commit()
                    except Exception:
                        pass

    except Exception as e:
        print(f"Migration check completed with notice/warning: {e}")
