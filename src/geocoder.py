import requests
import logging
from typing import Dict, Optional

# Don't need to create setting because already happening in scrapery.py?
# Creaates a logger module specifically for this file
logger = logging.getLogger(__name__)

# Optional[Dict], fucnction should return a dict but if it fails, it will be None and that's ok too
def get_city_coordinates(city_name: str) -> Optional[Dict]:
    """
    Fetches latitude, longitude, and bounding box for a given city name
    from Ameli's internal geocoding API.

    Args:
        city_name (str): The name of the city to search for.

    Returns:
        Optional[Dict]: A dictionary containing 'center_lat', 'center_lng', and 'bbox'
                        if successful. Returns None if the request fails or no city is found.
    """
    url = "https://annuairesante.ameli.fr/ansa-fo-api/recherche/adresse"

    params = {'adresse': city_name}
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://annuairesante.ameli.fr/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'X-CSRF-TOKEN': 'a6d9d4e0-8f60-4b4f-96f1-b490df9d437a',
        'correlationID': 'fd4bf124-28d9-462e-86ad-b32448b731fe',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        # 'Cookie': 'b09f5ce44cca9a42444523ebad089060=7d22903014d567b657f95ca3ee354a18; CSRF-TOKEN=a6d9d4e0-8f60-4b4f-96f1-b490df9d437a; 36ee771d8494ed0b335eeb257d2fd552=21fcaa867063cfce47dbce14c81fd789; TS016a8402=0139dce0d2379eb93949c6839cf1f10e258fce416fc71e6fba27157239cdf5fe2b3d298a209efe600712633cd8eb12a4b6675257c7; TS013c1982=0139dce0d27feedaaf5be4703326ced7cb79a9d69c7c0071de06af41f223fabe29ecaab2c47f9c68fbce4326d99042c50fb0e8f49c',
    }

    try:
        logger.info(f"Geocoding city: {city_name}")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if not data:
            logger.warning(f"No results found for city: {city_name}")
            return None
        
        first_result = data[0]
        geometry = first_result['geometry']

        #Exctract coordinates from nested structure - 
        center_lng, center_lat = geometry['centre']['coordinates']
        bbox_coordinates = geometry['bbox']['coordinates'][0] # Get inner list of coordinates

        #Transform list of [lon, lat] pairs into flat string format main API needs
        bbox_string = ",".join([f"{lon},{lat}" for lon, lat in bbox_coordinates])

        return {
            'center_lat': center_lat,
            'center_lng': center_lng,
            'bbox': bbox_string
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding API request failed for {city_name}: {e}")
        return None