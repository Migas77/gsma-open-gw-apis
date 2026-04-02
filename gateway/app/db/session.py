import os
from pymongo import AsyncMongoClient

client = AsyncMongoClient(
    os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
    username=os.environ.get("MONGO_USER", "root"),
    password=os.environ.get("MONGO_PASSWORD", "pass"),
    uuidRepresentation="standard",
)
db_mongo = client["camara"]

