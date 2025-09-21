#src/main.py
import logging
from sqlalchemy.orm import Session

# My modules
from .database import SessionLocal, engine
from .models import Base
from .scraper import scrape_doctors_for_city # Orchestrator function

# Set up logging
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

def main():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Create a db session
    db: Session = SessionLocal()
    try:
        logger.info("Starting scraping process...")

        scrape_doctors_for_city(
            db=db,
            city_name="Marseille",
            profession_id=37
        )

    except Exception as e:
        logger.error(f"An erroroccurred during the scraping process: {e}")
        # If something goes wrong, roll back db changes
        db.rollback()
    finally:
        # Always close db connection
        db.close()

if __name__=="__main__":
        main()