"""
MongoDB Atlas connection module for ComicCraft.
Run standalone to verify connectivity:
    python database.py
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "comiccraft")

client = MongoClient(MONGODB_URI)

db = client[MONGODB_DATABASE]

users_collection = db["users"]
comics_collection = db["comics"]
panels_collection = db["panels"]

# ── Connection test (runs only when executed directly) ─────────────────────────
if __name__ == "__main__":
    try:
        client.admin.command("ping")
        print("[OK] MongoDB Atlas connected successfully!")
        print(f"   Database    : {MONGODB_DATABASE}")
        print("   Collections :")
        for name in [users_collection.name, comics_collection.name, panels_collection.name]:
            print(f"     - {name}")
    except Exception as e:
        print("[FAIL] MongoDB connection failed:", e)
