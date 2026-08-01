import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError

from app.core.config import settings

logger = logging.getLogger("vocalsync.db")


class MongoDBClient:
    """
    Singleton asynchronous database client manager using Motor.
    Handles connection pooling, lifecycle management, and index initialization.
    """
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect_to_database(self) -> None:
        """
        Initializes the connection pool to MongoDB Atlas (or local MongoDB)
        and triggers automatic index creation for production collections.
        Called during FastAPI application startup.
        """
        logger.info("Connecting to MongoDB Async Client...")
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                maxPoolSize=50,  
                minPoolSize=5,   
                serverSelectionTimeoutMS=5000,
            )
            self.db = self.client[settings.MONGODB_DB_NAME]

            await self.client.admin.command("ping")
            logger.info(f"Successfully connected to MongoDB Database: '{settings.MONGODB_DB_NAME}'")

            await self._create_indexes()

        except ConnectionFailure as e:
            logger.critical(f"MongoDB Connection Failure: {e}")
            raise e
        except PyMongoError as e:
            logger.critical(f"MongoDB Initialization Error: {e}")
            raise e

    async def close_database_connection(self) -> None:
        """
        Gracefully terminates the Motor connection pool.
        Called during FastAPI application shutdown.
        """
        if self.client:
            logger.info("Closing MongoDB Motor connection pool...")
            self.client.close()
            logger.info("MongoDB connection pool closed.")

    async def _create_indexes(self) -> None:
        """
        Idempotent index creation to guarantee fast lookups on high-frequency
        queries (call history, lead status, and phone/email deduplication).
        """
        if self.db is None:
            return

        logger.info("Verifying and creating MongoDB indexes...")

        try:
            calls_indexes = [
                IndexModel([("call_id", ASCENDING)], unique=True, name="idx_calls_call_id"),
                IndexModel([("created_at", DESCENDING)], name="idx_calls_created_at"),
                IndexModel(
                    [("lead_status", ASCENDING), ("created_at", DESCENDING)],
                    name="idx_calls_status_created"
                ),
            ]
            await self.db.calls.create_indexes(calls_indexes)

            leads_indexes = [
                IndexModel([("email", ASCENDING)], unique=True, sparse=True, name="idx_leads_email"),
                IndexModel([("phone", ASCENDING)], unique=True, sparse=True, name="idx_leads_phone"),
                IndexModel([("qualification_score", DESCENDING)], name="idx_leads_score"),
                IndexModel([("updated_at", DESCENDING)], name="idx_leads_updated"),
            ]
            await self.db.leads.create_indexes(leads_indexes)

            logger.info("MongoDB indexes successfully verified/created.")

        except PyMongoError as e:
            logger.error(f"Failed to create MongoDB indexes: {e}")

    async def ping(self) -> bool:
        """
        Health probe method to check database responsiveness.
        Returns True if reachable, False otherwise.
        """
        try:
            if self.client:
                await self.client.admin.command("ping")
                return True
            return False
        except Exception as e:
            logger.warning(f"MongoDB health ping failed: {e}")
            return False

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Returns the active database instance. Raises an error if called before connect().
        """
        if self.db is None:
            raise RuntimeError("Database not initialized. Ensure connect_to_database() is called on startup.")
        return self.db


mongo_client = MongoDBClient()


def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency getter for retrieving the database instance.
    """
    return mongo_client.get_database()