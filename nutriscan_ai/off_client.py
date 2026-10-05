"""
off_client.py

OpenFoodFactsClient: thin wrapper around the Open Food Facts REST API.
Handles barcode lookups and name-based search, with robust error handling
for network failures, timeouts, and missing products.
"""

import requests

from exceptions import APIRequestError, ProductNotFoundError, InvalidBarcodeError
from models import FoodProduct, validate_barcode


class OpenFoodFactsClient:
    """Client for the free, keyless Open Food Facts API."""

    BASE_URL = "https://world.openfoodfacts.org"
    USER_AGENT = "NutriScanAI/1.0 (educational project)"
    TIMEOUT_SECONDS = 10

    def __init__(self, timeout: int = TIMEOUT_SECONDS):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    # ---------- Public methods ----------

    def get_by_barcode(self, barcode: str) -> FoodProduct:
        """
        Fetch a single product by barcode.
        Raises InvalidBarcodeError, APIRequestError, or ProductNotFoundError.
        """
        clean_barcode = validate_barcode(barcode)  # may raise InvalidBarcodeError
        url = f"{self.BASE_URL}/api/v2/product/{clean_barcode}.json"

        data = self._get_json(url)

        if data.get("status") != 1 or "product" not in data:
            raise ProductNotFoundError(f"No product found for barcode {clean_barcode}.")

        return FoodProduct.from_api_json(data)

    def search_by_name(self, query: str, limit: int = 10) -> list:
        """
        Search products by name/keyword. Returns a list of FoodProduct.
        Raises APIRequestError or ProductNotFoundError.
        """
        if not query or not query.strip():
            raise ProductNotFoundError("Search query cannot be empty.")

        url = f"{self.BASE_URL}/cgi/search.pl"
        params = {
            "search_terms": query.strip(),
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": limit,
        }

        data = self._get_json(url, params=params)
        products_raw = data.get("products", [])

        if not products_raw:
            raise ProductNotFoundError(f"No products found matching '{query}'.")

        results = []
        for raw in products_raw:
            try:
                results.append(FoodProduct.from_api_json({"product": raw}))
            except Exception:
                # Skip malformed individual entries rather than failing the whole search
                continue

        if not results:
            raise ProductNotFoundError(f"No usable product data found for '{query}'.")

        return results

    # ---------- Internal helpers ----------

    def _get_json(self, url: str, params: dict = None) -> dict:
        """Perform a GET request and return parsed JSON, wrapping any failure."""
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise APIRequestError("The request to Open Food Facts timed out. Please try again.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise APIRequestError("Could not connect to Open Food Facts. Check your internet connection.") from exc
        except requests.exceptions.HTTPError as exc:
            raise APIRequestError(f"Open Food Facts returned an error: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise APIRequestError(f"Unexpected request error: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise APIRequestError("Open Food Facts returned an invalid (non-JSON) response.") from exc
