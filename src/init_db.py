#src/init_db.py
from .database import engine, Base
from .models import Doctor

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created!")