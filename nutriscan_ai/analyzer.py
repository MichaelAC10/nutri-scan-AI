"""
analyzer.py

NutritionAnalyzer: classifies a FoodProduct's nutrient levels (sugar, fat,
saturated fat, salt, calories) as Low / Moderate / High using thresholds
based on UK FSA "traffic light" per-100g guidance, and produces a simple
allergen summary.
"""

from exceptions import IncompleteDataError
from models import FoodProduct


class NutritionAnalyzer:
    """Applies nutrition thresholds to a FoodProduct and produces a verdict."""

    # (low_max, moderate_max) per 100g — above moderate_max = High
    THRESHOLDS = {
        "sugar_g": (5.0, 22.5),
        "fat_g": (3.0, 17.5),
        "saturated_fat_g": (1.5, 5.0),
        "salt_g": (0.3, 1.5),
        "energy_kcal": (150, 400),  # rough general-purpose banding
    }

    LABELS = {
        "sugar_g": "Sugar",
        "fat_g": "Fat",
        "saturated_fat_g": "Saturated Fat",
        "salt_g": "Salt",
        "energy_kcal": "Calories",
    }

    def __init__(self, product: FoodProduct):
        self.product = product

    def analyze(self) -> dict:
        """
        Return a dict like:
        {
          "sugar_g": {"value": 12.3, "level": "High"},
          ...
          "allergens": [...],
          "missing": [...]
        }
        Raises IncompleteDataError if there isn't enough data to analyze at all.
        """
        if not self.product.is_complete():
            raise IncompleteDataError(
                f"'{self.product.name}' is missing key nutrition data "
                f"({', '.join(self.product.missing_fields())}) and cannot be fully analyzed."
            )

        results = {}
        for key, (low_max, mod_max) in self.THRESHOLDS.items():
            value = self.product.nutrients.get(key)
            results[key] = {
                "label": self.LABELS[key],
                "value": value,
                "level": self._classify(value, low_max, mod_max) if value is not None else "Unknown",
            }

        results["allergens"] = self.product.allergens
        results["missing"] = self.product.missing_fields()
        results["overall_flags"] = self._overall_flags(results)
        return results

    # ---------- Internal ----------

    @staticmethod
    def _classify(value: float, low_max: float, mod_max: float) -> str:
        if value is None:
            return "Unknown"
        if value <= low_max:
            return "Low"
        elif value <= mod_max:
            return "Moderate"
        else:
            return "High"

    @staticmethod
    def _overall_flags(results: dict) -> list:
        """Quick list of human-readable warnings for anything flagged High."""
        flags = []
        for key, info in results.items():
            if isinstance(info, dict) and info.get("level") == "High":
                flags.append(f"High in {info['label']}")
        return flags
