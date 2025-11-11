# backend/config.py
import os

# This is the single source of truth for our project's location.
# Use a raw string (r"...") with your standard Windows path.
PROJECT_ROOT = r"C:\Users\shara_4dzvod7\OneDrive\Desktop\Vision_Assistant"

# Define the database path using the root.
DB_PATH = os.path.join(PROJECT_ROOT, 'backend', 'memory.db')