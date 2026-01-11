import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ddns.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    # Check directory permissions
    data_dir = "/data"
    if os.path.exists(data_dir):
        stat_info = os.stat(data_dir)
        logger.info(f"Data directory {data_dir} exists with permissions: {oct(stat_info.st_mode)}")
    else:
        logger.error(f"Data directory {data_dir} does not exist")
        
    # Try to create a test file
    test_file = "/data/test.txt"
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.info("Successfully created and removed test file in /data")
    except Exception as e:
        logger.error(f"Cannot write to /data directory: {e}")
    
    # Log the DATABASE_URL being used
    logger.info(f"DATABASE_URL: {DATABASE_URL}")
    
    # Create all tables using SQLAlchemy
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()