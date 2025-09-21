#src/models.py
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from .database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String, index=True)
    first_name = Column(String)
    specialty = Column(String)
    address = Column(String)
    office_name = Column(String)
    city = Column(String)
    # Matches key in cities table creating a link between tables
    city_id = Column(Integer, ForeignKey("cities.city_id"))
    postal_code = Column(String)
    latitude = Column(Float(10, 7))
    longitude = Column(Float(10, 7))
    phone_number = Column(String)
    vitale_card = Column(Boolean, default=False)
    # sector_1_agmt = Column(Boolean, default=False)
    

class City(Base):
    __tablename__ = "cities"
    city_id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String, index=True)
    postal_code = Column(String)
    center_lat = Column(Float(10, 7))
    center_lng = Column(Float(10, 7))
    bbox = Column(String)
    