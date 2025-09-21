#src/scraper.py
import requests
import logging
import time
import random
from typing import Optional, Any
from sqlalchemy.orm import Session
from . import models # imports sqlalchemy models
from .geocoder import get_city_coordinates # import geocoder function
from .session import create_authenticated_session

# The basic settings for the Python logging module
# level=logging.INFO captures and displays all message levels of INFO or higher (WARNING, ERROR, CRITICAL)
# logging.basicConfig(level=logging.INFO)
# Creates a logger object specifically for this file
# __name__ ensures logger name matches module/filename, allows control of diff. parts of app later
logger = logging.getLogger(__name__)

def search_doctors_by_coordinates(
        session,
        profession_id: int,
        center_lat: float,
        center_lng: float,
        bbox_coordinates: str,
    ) -> Optional[dict[str, Any]]:
    """
    Fetches a list of doctors from the Ameli API based on geographic coordinates.
    Uses an authenticated session with dynamic CSRF and correlationID.
    """

    url = "https://annuairesante.ameli.fr/ansa-fo-api/recherche"
    params = {
        "nom": "",
        "idProfession": profession_id,
        "centre": f"{center_lng},{center_lat}",  # note: order is lng,lat
        "bbox": bbox_coordinates,
        "bboxElargie": "true",
        "professionType": "PROFESSION",
    }

    try:
        logger.info(f"Fetching doctor data for profession ID {profession_id}")
        delay_seconds = random.uniform(5, 12)
        logger.info(f"Polite delay: {delay_seconds: .2f}s")
        time.sleep(delay_seconds)

        response = session.get(url, params=params, timeout=30)

        #Debug logging
        logger.info(f"Full Request URL: {response.request.url}")
        logger.info(f"HTTP Status Code: {response.status_code}")

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            logger.error("Expected JSON but got non-JSON response. Likely blocked.")
            logger.debug(f"Response preview:\n{response.text[:500]}...")
            return None
        
        return response.json()
    
    except Exception as e:
        logger.error(f"API request failed: {e}")
    
    # except requests.exceptions.RequestException as e:
    #     logger.error(f"API request failed: {e}")
    #     if hasattr(e, "response") and e.response is not None:
    #         logger.error(f"Server responded with: {e.response.status_code}")
    #         logger.error(f"Response preview: {e.response.text[:500]}")
    #     return None

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

    # Create session for API calls
    session = create_authenticated_session()
    # Call the main doctors API with coordinates (cache-retrieved or new)
    doctors_data = search_doctors_by_coordinates(session, profession_id, center_lat, center_lng, bbox)

    if not doctors_data:
        logger.error(f"No doctor data retrieved for {city_name}. Skipping save.")
        return

    # Process and save doctors.
    doctor_list = doctors_data.get('data', [])
    for doctor_data in doctor_list:
        new_doctor = models.Doctor(
            first_name=doctor_data.get("prenom"),
            last_name=doctor_data.get("nom"),
            specialty=doctor_data["profession"]["specialite"]["libelle"]
            if doctor_data.get("profession")
            else None,
            city_id=db_city.city_id,
            address=doctor_data.get("voie"),
            office_name=doctor_data.get("complement"),
            city=doctor_data.get("ville"),
            postal_code=doctor_data.get("codePostal"),
            latitude=doctor_data.get("geocode", {}).get("latitude"),
            longitude=doctor_data.get("geocode", {}).get("longitude"),
            phone_number=doctor_data.get("coordonnees", {}).get("numTel"),
            vitale_card=doctor_data.get("carteVitale", False),
            # sector_1_agmt = doctor_data[''],
        )
        db.add(new_doctor)

    db.commit() # Saves all new docs at one time
    logger.info(f"Saved {len(doctor_list)} doctors for {city_name}")




# def search_doctors_by_coordinates(profession_id: int, center_lat: float, center_lng: float, bbox_coordinates: str) -> Optional[dict[str, Any]]:
    
#     """
#     Fetches a list of doctors from the Ameli API based on geographic coordinates.

#     Args:
#         profession_id (int or str): The unique identifier for the medical specialty (e.g., 37 for 'Médecin généraliste').
#         center_lat (float): The latitude of the center point for the search area.
#         center_lng (float): The longitude of the center point for the search area.
#         bbox_coordinates (str): A string of coordinates defining the bounding box of the search area.

#     Returns:
#         dict or None: A dictionary containing the JSON response from the API if the request is successful.
#         Returns None if the request fails (e.g., network error, invalid response).
#     """

#     # GET request address
#     url = "https://annuairesante.ameli.fr/ansa-fo-api/recherche"

#     # Params dict holds the query params to append to URL
#     params = {
#         'nom': '',
#         'idProfession': profession_id,
#         'centre': f"{center_lng},{center_lat}",
#         # The box in which to seach, str sequence of long, lat pairs as vertices
#         'bbox': bbox_coordinates,
#         'bboxElargie': 'true',
#         'professionType': 'PROFESSION'
#     }

#     # Use new session instead of raw request.
#     session = create_authenticated_session()

#     # Headers dict allows sending of addtl. information about the request to the server
#     # headers = {
#     #     # Identifies client software to server, descriptive is best practice, helps avoid being blocked
#     #     # 'User-Agent': 'Student=Project-Data-Collection (https://github.com/WhitShake/ameli-scraper)'
#     #     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#     #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
#     #     'Accept-Language': 'en-US,en;q=0.9',
#     #     'Accept-Encoding': 'gzip, deflate, br',
#     #     'Connection': 'keep-alive',
#     #     'Referer': 'https://annuairesante.ameli.fr/', # This is very important
#     #     'Sec-Fetch-Dest': 'document',
#     #     'Sec-Fetch-Mode': 'navigate',
#     #     'Sec-Fetch-Site': 'same-origin',
#     #     'Sec-Fetch-User': '?1',
#     #     'Upgrade-Insecure-Requests': '1',
#     #     'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
#     #     'Sec-Ch-Ua-Mobile': '?0',
#     #     'Sec-Ch-Ua-Platform': '"macOS"',
#     # }

#     # Output message, unlike print, can be turned on/off easily
#     # logger.info(f"Fetching data from API for profession ID: {profession_id}")

#     # Handle errors gracefully
#     try:
#         # Send the HTTP GET request to the constructed URL.
#         # - 'url': the API endpoint
#         # - 'params': the query parameters are automatically encoded and added to the URL
#         # - 'headers': our custom headers are included
#         # - 'timeout=30': tells requests to stop waiting for a response after 30 seconds.
#         #   This prevents the script from hanging indefinitely on a slow or dead connection.

#         logger.info(f"Fetching data from API for profession ID: {profession_id}")

#         delay_seconds = random.uniform(5, 15)
#         logger.info(f"Being polite: waiting for {delay_seconds:.2f} seconds before requesting...")
#         time.sleep(delay_seconds)

#         response = session.get(url, params=params, timeout=30)

#         # Debugging:
#         logger.info(f"Full Request URL: {response.request.url}")
#         logger.info(f"HTTP Status Code: {response.status_code}")
#         # Check if response is empty before trying to preview:
#         if response.text:
#             logger.info(f"Response Text Preview: {response.text[:500]}...") # First 500 chars
#         else:
#             logger.info("Response body is completely empty.")

#         # Checks HTTP status for response, if it's a clinet (4XX) or server (5XX) this method
#         # will raise an exception
#         response.raise_for_status()

#         # If resquest was susccessful, parse response body as JSON and return
#         # .json() method converts the JSON response string into dict.
#         return response.json()
    
#     # Catches any exception the 'requests' library might throw (network errors, timeouts, etc)
#     except requests.exceptions.RequestException as e:
#         # Log the error message
#         logger.error(f"API request failed: {e}")
#         # If it's a response error, log the server's response
#         if hasattr(e, 'response') and e.response is not None:
#             logger.error(f"Server responded with: {e.response.status_code}")
#             logger.error(f"Response content: {e,response.text[:1000]}")
#         return None
    
# # The code inside this block will only execute if you run `python src/scraper.py` from the command line.
# if __name__ == "__main__":
#     # Currently hardcoded but will be auto-generated for each city
#     profession_id = 37 # ID for the Médicin géneraliste
#     center_lat = 43.2803 # Approx. lat of central Marseille
#     center_lng = 5.3806
#     # A string defining a geographic box around Marseille.
#     # The format is: long1,lat1, long2,lat2, long3,lat3, long4,lat4, long1,lat1
#     # (It lists the vertices of the polygon, closing the loop with the first point).
#     bbox = "5.228751,43.169636,5.532543,43.169636,5.532543,43.391057,5.228751,43.391057,5.228751,43.169636"

#     # Call the function with above test parameters & store result.
#     data = search_doctors_by_coordinates(profession_id, center_lat, center_lng, bbox)

#     # Check if funtion returned data
#     if data:
#         # .get('data', [])) safely tries to get the 'data' key from reponse
#         # If data doesn't exist, returns an empty list instead of crashing
#         num_results = len(data.get('data', []))
#         print(f"Success! Found {num_results} results.")

#         # Save raw entire raw API response to a file for debugging without repeated calls
#         import json # Only needed in this block - import here

#         filename = 'data/api_sample.json'
#         # Open file for writing ('w'), 'encoding='utf-8'' - ensures French chars saved correctly
#         with open(filename, 'w', encoding='utf-8') as f:
#             #json.dump()) writes the Python dict data to file 'f'
#             # indent=4 formats JSON with indentation for legibility
#             # ensure_ascii=False non-ASCII chars (é, å) can be written as is
#             json.dump(data, f, indent=4, ensure_ascii=False)
#         print(f"Raw API response saved to {filename}")