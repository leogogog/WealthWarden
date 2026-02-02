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
        # 1. Check & Fix 'assets' table
        print("Checking 'assets' table columns...")
        cursor.execute("PRAGMA table_info(assets)")
        # row[1] is name, row[2] is type
        existing_cols = {row[1]: row[2] for row in cursor.fetchall()}
        
        if not existing_cols:
            print("⚠️ Table 'assets' not found or empty. Skipping.")
        else:
            # list of (col_name, col_type, default_val)
            required_columns = [
                ("category", "TEXT", "'OTHERS'"),
                ("currency", "TEXT", "'CNY'"),
                ("balance", "FLOAT", "0.0"),
                ("updated_at", "DATETIME", "CURRENT_TIMESTAMP"),
                ("type", "TEXT", "'LIQUID'"),
                ("credit_limit", "FLOAT", "NULL"),
                ("billing_day", "INTEGER", "NULL")
            ]
            
            for col_name, col_type, default_val in required_columns:
                if col_name not in existing_cols:
                    print(f"🛠 Adding missing '{col_name}' column...")
                    # SQLite ADD COLUMN syntax
                    if col_type == "DATETIME":
                        cursor.execute(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type}")
                    else:
                        cursor.execute(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
                    conn.commit()
                    print(f"✅ Fixed: Added '{col_name}' column.")
                else:
                    print(f"✅ '{col_name}' column exists.")

        # 2. Check & Fix 'transactions' table
        print("\nChecking 'transactions' table columns...")
        cursor.execute("PRAGMA table_info(transactions)")
        existing_tx_cols = {row[1]: row[2] for row in cursor.fetchall()}

        if "asset_id" not in existing_tx_cols:
            print("🛠 Adding missing 'asset_id' column to 'transactions'...")
            cursor.execute("ALTER TABLE transactions ADD COLUMN asset_id INTEGER REFERENCES assets(id)")
            conn.commit()
            print("✅ Fixed: Added 'asset_id' column.")
        else:
            print("✅ 'asset_id' column exists.")

        # 3. Create 'budgets' table if not exists
        print("\nChecking 'budgets' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budgets'")
        if not cursor.fetchone():
            print("🛠 Creating 'budgets' table...")
            cursor.execute("""
                CREATE TABLE budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR UNIQUE,
                    limit_amount FLOAT NOT NULL,
                    currency VARCHAR DEFAULT 'CNY',
                    alert_threshold FLOAT DEFAULT 0.8,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX ix_budgets_category ON budgets (category)")
            cursor.execute("CREATE INDEX ix_budgets_id ON budgets (id)")
            conn.commit()
            print("✅ Fixed: Created 'budgets' table.")
        else:
            print("✅ 'budgets' table exists.")

        print("\n🎉 Database upgrade completed successfully!")
        
    except Exception as e:
        print(f"\n❌ detailed error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()
