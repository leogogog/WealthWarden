import sqlite3
import os
import sys

# Define the path to the database
# In Docker, it's mapped to /opt/finance_bot/data/finance.db
# We check common locations
POSSIBLE_PATHS = [
    "data/finance.db",
    "/opt/finance_bot/data/finance.db",
    "finance.db"
]

def find_db():
    for path in POSSIBLE_PATHS:
        if os.path.exists(path):
            return path
    return None

def upgrade_database():
    print("--- Database Upgrade Tool ---")
    db_path = find_db()
    
    if not db_path:
        print("❌ Error: Could not find 'finance.db'.")
        print(f"Searched in: {POSSIBLE_PATHS}")
        print("Please run this script from the project root or check your volume mapping.")
        return

    print(f"Found database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Check & Fix 'assets' table for 'category'
        print("Checking 'assets' table...")
        cursor.execute("PRAGMA table_info(assets)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            print("⚠️ Table 'assets' not found or empty. Skipping.")
        elif "category" in columns:
            print("✅ 'category' column already exists.")
        else:
            print("🛠 Adding missing 'category' column...")
            cursor.execute("ALTER TABLE assets ADD COLUMN category TEXT DEFAULT 'OTHERS'")
            conn.commit()
            print("✅ Fixed: Added 'category' column.")

        # 2. Check & Fix 'assets' table for 'currency' (just in case)
        if columns and "currency" not in columns:
            print("🛠 Adding missing 'currency' column...")
            cursor.execute("ALTER TABLE assets ADD COLUMN currency TEXT DEFAULT 'CNY'")
            conn.commit()
            print("✅ Fixed: Added 'currency' column.")
            
        print("\n🎉 Database upgrade completed successfully!")
        
    except Exception as e:
        print(f"\n❌ detailed error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()
