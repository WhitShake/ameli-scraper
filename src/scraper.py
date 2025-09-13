from sqlalchemy.orm import Session
from . import models # imports sqlalchemy models
from .geocoder import get_city_coordinates # import geocoder function
# API Client Function
import requests
# This is a more powerful alternative to using print() statements.
# It allows creation of formatted messages with different levels of importance (INFO, WARNING, ERROR).
import logging
from typing import Optional, List, Any

# The basic settings for the Python logging module
# level=logging.INFO captures and displays all message levels of INFO or higher (WARNING, ERROR, CRITICAL)
logging.basicConfig(level=logging.INFO)
# Creates a logger object specifically for this file
# __name__ ensures logger name matches module/filename, allows control of diff. parts of app later
logger = logging.getLogger(__name__)

def scrape_doctors_for_city(db: Session, city_name: str, profession_id: int) -> None:
    """
    Main orchestrator funtion to find and store doctors for a given city
    """

    # Check db first, city may already be in table.
    db_city = db.query(models.City).filter(models.City.city_name == city_name).first()

    # City in db.
    if db_city:
        center_lat = db_city.center_lat
        center_lng = db_city.center_lng
        bbox = db_city.bbox
        logger.info(f"using cached coordinates for {city_name}")

    else:
        # City not in db, geocode/make API call to Ameli
        logger.info(f"City {city_name} not found in cache. Geocoding...")
        coords = get_city_coordinates(city_name)

        if not coords:
            logger.error(f"Failed to geocode city: {city_name}")
            return
        
        center_lat = coords['center_lat']
        center_lng = coords['center_lng']
        bbox = coords['bbox']

        # Create new db entry for new city data
        new_city = models.City(
            city_name = city_name,
            center_lat = center_lat,
            center_lng = center_lng,
            bbox = bbox
        )

        db.add(new_city)
        db.commit() # Save the new city to the db
        db.refresh(new_city) # Get the newly generated city_id
        logger.info(f"Saved new city to DB: {city_name} (ID: {new_city.city_id})")

        db_city = new_city

        # Call the main doctors API with coordinates (cache-retrieved or new)
        doctors_data = search_doctors_by_coordinates(profession_id, center_lat, center_lng, bbox)

        # Process and save each doctor.
        for doctor_data in doctors_data.get('data', []):
            new_doctor = models.Doctor(
                first_name = doctor_data['prenom'],
                last_name = doctor_data['nom'],
                specialty=doctor_data['profession']['specialite']['libelle'],
                city_id=db_city.city_id,
                address = doctor_data['voie'],
                office_name = doctor_data['complement'],
                city = doctor_data['ville'],
                postal_code = doctor_data['codePostal'],
                latitude = doctor_data['geocode']['latitude'],
                longitude = doctor_data['geocode']['longitude'],
                phone_number = doctor_data['coordonnees']['numTel'],
                vitale_card = doctor_data['carteVitale'],
                # sector_1_agmt = doctor_data[''],
            )

            db.add(new_doctor)
        db.commit() # Saves all new docs at one time
        logger.info(f"Saved {len(doctors_data.get('data', []))} doctors for {city_name}")



def search_doctors_by_coordinates(profession_id: int, center_lat: float, center_lng: float, bbox_coordinates: str) -> Optional[dict[str, Any]]:
    
    """
    Fetches a list of doctors from the Ameli API based on geographic coordinates.

    Args:
        profession_id (int or str): The unique identifier for the medical specialty (e.g., 37 for 'Médecin généraliste').
        center_lat (float): The latitude of the center point for the search area.
        center_lng (float): The longitude of the center point for the search area.
        bbox_coordinates (str): A string of coordinates defining the bounding box of the search area.

    Returns:
        dict or None: A dictionary containing the JSON response from the API if the request is successful.
        Returns None if the request fails (e.g., network error, invalid response).
    """

    # GET request address
    url = "https://annuairesante.ameli.fr/ansa-fo-api/recherche"

    # Params dict holds the query params to append to URL
    params = {
        'nom': '',
        'idProfession': profession_id,
        'centre': f"{center_lng}, {center_lat}",
        # The box in which to seach, str sequence of long, lat pairs as vertices
        'bbox': bbox_coordinates,
        'bboxElargie': 'true',
        'professionType': 'PROFESSION'
    }

    # Headers dict allows sending of addtl. information about the request to the server
    headers = {
        # Identifies client software to server, descriptive is best practice, helps avoid being blocked
        'User-Agent': 'Student=Project-Data-Collection (https://github.com/WhitShake/ameli-scraper)'
    }

    # Output message, unlike print, can be turned on/off easily
    logger.info(f"Fetching data from API for profession ID: {profession_id}")

    # Handle errors gracefully
    try:
        # Send the HTTP GET request to the constructed URL.
        # - 'url': the API endpoint
        # - 'params': the query parameters are automatically encoded and added to the URL
        # - 'headers': our custom headers are included
        # - 'timeout=30': tells requests to stop waiting for a response after 30 seconds.
        #   This prevents the script from hanging indefinitely on a slow or dead connection.
        response = requests.get(url, params=params, headers=headers, timeout=30)

        # Checks HTTP status for response, if it's a clinet (4XX) or server (5XX) this method
        # will raise an exception
        response.raise_for_status()

        # If resquest was susccessful, parse response body as JSON and return
        # .json() method converts the JSON response string into dict.
        return response.json()
    
    # Catches any exception the 'requests' library might throw (network errors, timeouts, etc)
    except requests.exceptions.RequestException as e:
        # Log the error message
        logger.error(f"API request failed: {e}")
        return None
    
# The code inside this block will only execute if you run `python src/scraper.py` from the command line.
if __name__ == "__main__":
    # Currently hardcoded but will be auto-generated for each city
    profession_id = 37 # ID for the Médicin géneraliste
    center_lat = 43.2803 # Approx. lat of central Marseille
    center_lng = 5.3806
    # A string defining a geographic box around Marseille.
    # The format is: long1,lat1, long2,lat2, long3,lat3, long4,lat4, long1,lat1
    # (It lists the vertices of the polygon, closing the loop with the first point).
    bbox = "5.228751,43.169636,5.532543,43.169636,5.532543,43.391057,5.228751,43.391057,5.228751,43.169636"

    # Call the function with above test parameters & store result.
    data = search_doctors_by_coordinates(profession_id, center_lat, center_lng, bbox)

    # Check if funtion returned data
    if data:
        # .get('data', [])) safely tries to get the 'data' key from reponse
        # If data doesn't exist, returns an empty list instead of crashing
        num_results = len(data.get('data', []))
        print(f"Success! Found {num_results} results.")

        # Save raw entire raw API response to a file for debugging without repeated calls
        import json # Only needed in this block - import here

        filename = 'data/api_sample.json'
        # Open file for writing ('w'), 'encoding='utf-8'' - ensures French chars saved correctly
        with open(filename, 'w', encoding='utf-8') as f:
            #json.dump()) writes the Python dict data to file 'f'
            # indent=4 formats JSON with indentation for legibility
            # ensure_ascii=False non-ASCII chars (é, å) can be written as is
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Raw API response saved to {filename}")