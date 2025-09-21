import requests
import logging
import re
import uuid

logger = logging.getLogger(__name__)

def create_authenticated_session() -> requests.Session:
    """ 
    Creates a requests session that mimics a browser and prepares headers for
    Ameli's API calls. Skips CSRF (unreliable) and uses dynamic
    correlationID to look more like real client.
    """
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # "Accept": "application/json, text/plain, */*",
        # "Accept-Language": "en-US,en;q=0.9",
        # "Connection": "keep-alive",
        # "X-Requested-With": "XMLHttpRequest",
        # "correlationID": str(uuid.uuid4()),  # generate unique ID for each session
    })

    logger.info("Fetching search page to establish session...")
    res = session.get("https://annuairesante.ameli.fr/recherche/", timeout=10)
    res.raise_for_status()

    # Step 2: Extract CSRF token from HTML meta tag
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', res.text)
    if not match:
        logger.error("Could not extract CSRF token. Response snippet: ")
        logger.error(res.text[:500])
        raise RuntimeError("Could not extract CSRF token from search page.")
    csrf_token = match.group(1)

    # Step 3: Update headers for API calls
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": csrf_token,
        "correlationID": str(uuid.uuid4()),
    })

    logger.info(f"Authenticated session created successfully (CSRF: {csrf_token[:9]})")
    return session