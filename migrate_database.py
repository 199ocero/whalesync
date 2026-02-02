"""
Database Migration Script
Adds asset and resolution_time columns to existing paper_trades table
"""

import sqlite3
import config

def migrate_database():
    """Add new columns to paper_trades table"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(paper_trades)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add asset column if it doesn't exist
    if 'asset' not in columns:
        print("Adding 'asset' column to paper_trades table...")
        cursor.execute("ALTER TABLE paper_trades ADD COLUMN asset TEXT")
        print("✓ Added 'asset' column")
    else:
        print("'asset' column already exists")
    
    # Add resolution_time column if it doesn't exist
    if 'resolution_time' not in columns:
        print("Adding 'resolution_time' column to paper_trades table...")
        cursor.execute("ALTER TABLE paper_trades ADD COLUMN resolution_time TEXT")
        print("✓ Added 'resolution_time' column")
    else:
        print("'resolution_time' column already exists")
    
    conn.commit()
    conn.close()
    print("\n✓ Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()
