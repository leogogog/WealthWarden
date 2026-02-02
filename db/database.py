from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file - stored in a 'data' folder for better Docker volume mounting
DATABASE_URL = "sqlite:///data/finance.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import os
    from sqlalchemy import text
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    
    # --- Auto-Migration: Fix missing columns ---
    # This handles the case where the table exists but new columns (like 'category' in 'assets') are missing.
    with engine.connect() as conn:
        try:
            # Check assets table
            result = conn.execute(text("PRAGMA table_info(assets)"))
            columns = [row.name for row in result.fetchall()]
            
            if columns and 'category' not in columns:
                print("Migrating: Adding 'category' column to 'assets' table...")
                conn.execute(text("ALTER TABLE assets ADD COLUMN category VARCHAR"))
                conn.commit()
                
            # Check transactions table (just in case)
            result = conn.execute(text("PRAGMA table_info(transactions)"))
            columns = [row.name for row in result.fetchall()]
            
            # Example: If we added currency later, we'd check it here. 
            # for now, transactions seems stable.
            
        except Exception as e:
            print(f"Migration warning: {e}")

