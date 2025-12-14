# backend/init_db.py
import sqlite3
from config import DB_PATH # <--- IMPORT THE PATH

# Connect to the database using the absolute path from our config.
connection = sqlite3.connect(DB_PATH) 
cursor = connection.cursor()

# Create the 'locations' table.
cursor.execute('''
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
)
''')

# Create a small settings table for persisted calibration and preferences
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

connection.commit()
connection.close()

print(f"Database at '{DB_PATH}' initialized successfully.")