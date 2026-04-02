import uuid
from pymongo.asynchronous.database import AsyncDatabase
from typing import Any

# CREATE
async def create(db: AsyncDatabase, collection_name: str, json_data: Any, generate_uuid: bool = False):
    if generate_uuid:
        json_data.update({"_id": uuid.uuid4()})
    return await db[collection_name].insert_one(json_data)

# READ
async def read_all(db: AsyncDatabase, collection_name: str, res_filter: dict[str, Any]):
    collection = db[collection_name]
    return await collection.find(res_filter, {"_id": False}).to_list()

async def read_by_id(db: AsyncDatabase, collection_name: str, _id: str | uuid.UUID):
    collection = db[collection_name]
    return await collection.find_one({"_id": _id}, {"_id": False})

# UPDATE
async def replace_update_by_id(db: AsyncDatabase, collection_name: str, _id: str | uuid.UUID, json_data: dict[str, Any]):
    return await db[collection_name].find_one_and_replace({"_id": _id}, json_data, projection={"_id": 0})

# DELETE
async def delete_by_id(db: AsyncDatabase, collection_name: str, _id: str | uuid.UUID):
    return await db[collection_name].delete_one({"_id": _id})

