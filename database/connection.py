"""
Shared MongoDB connection for every OMNI agent and service.

Import `db` from here instead of building a MongoClient in each
module. One process should hold exactly ONE client, because every
MongoClient opens its own connection pool (up to 100 connections
by default) — seven agents each building their own would exhaust
the connection limit of a shared Atlas cluster.

Usage:

    from database.connection import db

    inventory_collection = db["inventory"]
"""

import os

from pymongo import MongoClient
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, "backend", ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

# Allows tests to run against a throwaway database without
# touching the shared team cluster.
DATABASE_NAME = os.getenv("MONGO_DB_NAME", "OMNI_DB")


if not MONGO_URI:

    raise RuntimeError(
        "MONGO_URI not found. Create backend/.env and set "
        "MONGO_URI to your MongoDB connection string."
    )


# ============================================================
# CLIENT
# ============================================================
#
# Module-level, so Python's import cache guarantees a single
# client — and therefore a single connection pool — per process.

client = MongoClient(MONGO_URI)

db = client[DATABASE_NAME]


# ============================================================
# HEALTH CHECK
# ============================================================

def check_connection():
    """
    Verify the cluster is reachable. Returns True on success.
    """

    try:

        client.admin.command("ping")

        print(f"Connected to MongoDB database '{DATABASE_NAME}'.")

        return True

    except Exception as error:

        print(f"Error connecting to MongoDB: {error}")

        return False
