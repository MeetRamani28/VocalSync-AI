import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from app.core.config import settings

logger = logging.getLogger("vocalsync.db")

class MongoDBClient:
    """
    Singleton async MongoDB Motor client with automatic index management.
    """
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls) -> None:
        """
        Establishes connection pool and verifies database indexes.
        """
        try:
            logger.info("Connecting to MongoDB Async Client...")
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            await cls.client.admin.command("ping")
            logger.info(f"Successfully connected to MongoDB Database: '{settings.MONGODB_DB_NAME}'")
            
            await cls._create_indexes()
        except Exception as e:
            logger.critical(f"Failed to connect to MongoDB: {e}", exc_info=True)
            raise e

    @classmethod
    async def _create_indexes(cls) -> None:
        """
        Creates unique and sparse indexes for calls, leads, and businesses collections.
        """
        try:
            logger.info("Verifying and creating MongoDB indexes...")
            
            call_indexes = [
                IndexModel([("call_id", ASCENDING)], unique=True, name="idx_calls_call_id"),
                IndexModel([("created_at", ASCENDING)], name="idx_calls_created_at"),
                IndexModel([("phone_number", ASCENDING)], name="idx_calls_phone_number")
            ]
            await cls.db.calls.create_indexes(call_indexes)

            lead_indexes = [
                IndexModel([("lead_id", ASCENDING)], unique=True, name="idx_leads_lead_id"),
                IndexModel([("call_id", ASCENDING)], unique=True, name="idx_leads_call_id"),
                IndexModel([("email", ASCENDING)], unique=True, sparse=True, name="idx_leads_email_sparse"),
                IndexModel([("phone", ASCENDING)], unique=True, sparse=True, name="idx_leads_phone_sparse")
            ]
            await cls.db.leads.create_indexes(lead_indexes)

            business_indexes = [
                IndexModel([("business_id", ASCENDING)], unique=True, name="idx_business_id"),
                IndexModel([("company_name", ASCENDING)], name="idx_company_name")
            ]
            await cls.db.businesses.create_indexes(business_indexes)

            logger.info("MongoDB indexes successfully verified/created.")
        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {e}")

    @classmethod
    async def close(cls) -> None:
        """
        Closes MongoDB connection pool gracefully on server shutdown.
        """
        if cls.client:
            cls.client.close()
            logger.info("MongoDB Async Client connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """
    Dependency helper returning the active async database instance.
    """
    if MongoDBClient.db is None:
        raise RuntimeError("MongoDB client is not initialized. Check startup event.")
    return MongoDBClient.db