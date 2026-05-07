import os
from pymongo import MongoClient
from datetime import datetime

# FIXME We have to install mongo but the msi dont install it correctly
client = MongoClient(os.getenv(MONGO_URI))
db = client[os.getenv(MONGO_DB)]
collection = db[os.getenv(MONGO_COLLECTION)]

def save_products(products: list[dict], supermarket: str) -> None:
    if not products:
        print("No products to save.")
        return

    # Agregar metadata a cada producto
    docs = [
        {
            **product,
            "supermarket": supermarket,
            "scraped_at": datetime.now(),
        }
        for product in products
    ]

    result = collection.insert_many(docs)
    print(f"  Saved {len(result.inserted_ids)} products to MongoDB")