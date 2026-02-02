import sqlite3
import os

DB_PATH = "data/finance.db"

def fix_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}. Nothing to fix.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check columns in assets table
    try:
        cursor.execute("PRAGMA table_info(assets)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            print("Table 'assets' does not exist or empty info.")
            return

        if "category" not in columns:
            print("Missing 'category' column in 'assets' table. Adding it...")
            cursor.execute("ALTER TABLE assets ADD COLUMN category VARCHAR")
            conn.commit()
            print("Successfully added 'category' column.")
        else:
            print("'category' column already exists.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_schema()
