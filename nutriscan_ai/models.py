"""
models.py

Defines FoodProduct: a clean, structured representation of a product
pulled from the Open Food Facts API's messy raw JSON.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# Nutrition fields we care about, mapped to the keys Open Food Facts uses
# inside "nutriments" (per 100g values).
_NUTRIENT_KEYS = {
    "energy_kcal": "energy-kcal_100g",
    "sugar_g": "sugars_100g",
    "fat_g": "fat_100g",
    "saturated_fat_g": "saturated-fat_100g",
    "salt_g": "salt_100g",
    "sodium_g": "sodium_100g",
    "fiber_g": "fiber_100g",
    "protein_g": "proteins_100g",
    "carbs_g": "carbohydrates_100g",
}

# Common allergens Open Food Facts tags as "en:milk", "en:gluten", etc.
_ALLERGEN_PATTERN = re.compile(r"en:([a-z0-9\-]+)", re.IGNORECASE)


@dataclass
class FoodProduct:
    """Structured product data used throughout the app."""

    barcode: Optional[str] = None
    name: str = "Unknown product"
    brand: str = ""
    ingredients_text: str = ""
    nutrients: dict = field(default_factory=dict)
    allergens: list = field(default_factory=list)
    image_url: Optional[str] = None

    # ---------- Construction ----------

    @classmethod
    def from_api_json(cls, raw: dict) -> "FoodProduct":
        """
        Build a FoodProduct from a raw Open Food Facts 'product' dict.
        Missing fields are tolerated; they simply come through as
        empty/None and get caught later by is_complete().
        """
        product = raw.get("product", raw) or {}

        nutriments = product.get("nutriments", {}) or {}
        nutrients = {}
        for clean_key, off_key in _NUTRIENT_KEYS.items():
            value = nutriments.get(off_key)
            nutrients[clean_key] = extract_number(value) if value is not None else None

        allergens_raw = product.get("allergens_tags", []) or []
        allergens = [cls._clean_allergen_tag(tag) for tag in allergens_raw]

        food = cls(
            barcode=product.get("code") or product.get("_id"),
            name=product.get("product_name") or product.get("generic_name") or "Unknown product",
            brand=product.get("brands", ""),
            ingredients_text=product.get("ingredients_text", "") or "",
            nutrients=nutrients,
            allergens=allergens,
            image_url=product.get("image_front_url") or product.get("image_url"),
        )
        food.ingredients_text = food.clean_ingredients()
        return food

    @staticmethod
    def _clean_allergen_tag(tag: str) -> str:
        match = _ALLERGEN_PATTERN.match(tag)
        cleaned = match.group(1) if match else tag
        return cleaned.replace("-", " ").title()

    # ---------- Regex-based cleaning ----------

    def clean_ingredients(self) -> str:
        """
        Clean raw ingredients text:
        - remove bracketed percentages/E-numbers like (E330) or (2.5%)
        - collapse repeated whitespace
        - strip stray punctuation left behind
        """
        if not self.ingredients_text:
            return ""

        text = self.ingredients_text
        text = re.sub(r"\(E\d{3,4}[a-zA-Z]?\)", "", text)      # (E330)
        text = re.sub(r"\(\s*\d+(\.\d+)?\s*%\s*\)", "", text)  # (2.5%)
        text = re.sub(r"\s{2,}", " ", text)                    # collapse whitespace
        text = re.sub(r"\s+([,.])", r"\1", text)                # space before punctuation
        return text.strip(" ,.")

    # ---------- Completeness check ----------

    def is_complete(self) -> bool:
        """
        True if we have enough data to run a meaningful nutrition analysis.
        We require at least calories + one of sugar/fat/salt to be present.
        """
        has_calories = self.nutrients.get("energy_kcal") is not None
        has_one_macro = any(
            self.nutrients.get(k) is not None for k in ("sugar_g", "fat_g", "salt_g")
        )
        return has_calories and has_one_macro

    def missing_fields(self) -> list:
        """List which of our tracked nutrient fields are missing (None)."""
        return [k for k, v in self.nutrients.items() if v is None]


def extract_number(value) -> Optional[float]:
    """
    Pull a float out of a nutrition value that might be a number already,
    or a messy string like '12.5 g', '  3,4 ', '<1', etc.
    Returns None if no number can be found.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(",", ".")
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def validate_barcode(barcode: str) -> str:
    """
    Validate a barcode string (EAN-8, UPC-A/EAN-13, or ITF-14: 8, 12, 13,
    or 14 digits). Returns the cleaned barcode (digits only) or raises
    InvalidBarcodeError.
    """
    from exceptions import InvalidBarcodeError  # local import avoids circularity at module load

    if barcode is None:
        raise InvalidBarcodeError("No barcode provided.")

    cleaned = re.sub(r"[\s\-]", "", barcode.strip())

    if not re.fullmatch(r"\d{8}|\d{12}|\d{13}|\d{14}", cleaned):
        raise InvalidBarcodeError(
            f"'{barcode}' is not a valid barcode. Expected 8, 12, 13, or 14 digits."
        )
    return cleaned
