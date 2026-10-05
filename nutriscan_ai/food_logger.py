"""
food_logger.py

FoodLogger: saves scanned products + their analysis to a local food log
file (CSV or JSON) and loads history back for display/export.
"""

import csv
import json
import os
from datetime import datetime

from exceptions import FoodLogError
from models import FoodProduct


class FoodLogger:
    """Persists scanned product entries to disk in CSV or JSON format."""

    CSV_FIELDS = [
        "timestamp", "name", "brand", "barcode",
        "energy_kcal", "sugar_g", "fat_g", "saturated_fat_g", "salt_g",
        "sugar_level", "fat_level", "salt_level",
        "allergens", "flags",
    ]

    def __init__(self, filepath: str = "food_log.csv"):
        self.filepath = filepath
        self.format = "json" if filepath.lower().endswith(".json") else "csv"

    # ---------- Public methods ----------

    def save_entry(self, product: FoodProduct, analysis: dict) -> None:
        """Append one scanned product + its analysis to the log file."""
        entry = self._build_entry(product, analysis)
        try:
            if self.format == "json":
                self._append_json(entry)
            else:
                self._append_csv(entry)
        except OSError as exc:
            raise FoodLogError(f"Could not write to log file '{self.filepath}': {exc}") from exc

    def load_log(self) -> list:
        """Return all saved log entries as a list of dicts (empty if no file yet)."""
        if not os.path.exists(self.filepath):
            return []

        try:
            if self.format == "json":
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                with open(self.filepath, "r", encoding="utf-8", newline="") as f:
                    return list(csv.DictReader(f))
        except (OSError, json.JSONDecodeError, csv.Error) as exc:
            raise FoodLogError(f"Could not read log file '{self.filepath}': {exc}") from exc

    def export_log(self, export_path: str, export_format: str = "csv") -> str:
        """Export the current log to a new file in the requested format."""
        entries = self.load_log()
        try:
            if export_format == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(entries, f, indent=2, ensure_ascii=False)
            else:
                with open(export_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                    writer.writeheader()
                    for row in entries:
                        writer.writerow({k: row.get(k, "") for k in self.CSV_FIELDS})
        except OSError as exc:
            raise FoodLogError(f"Could not export log to '{export_path}': {exc}") from exc
        return export_path

    # ---------- Internal helpers ----------

    @staticmethod
    def _build_entry(product: FoodProduct, analysis: dict) -> dict:
        def val(key):
            return analysis.get(key, {}).get("value")

        def level(key):
            return analysis.get(key, {}).get("level")

        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "name": product.name,
            "brand": product.brand,
            "barcode": product.barcode or "",
            "energy_kcal": val("energy_kcal"),
            "sugar_g": val("sugar_g"),
            "fat_g": val("fat_g"),
            "saturated_fat_g": val("saturated_fat_g"),
            "salt_g": val("salt_g"),
            "sugar_level": level("sugar_g"),
            "fat_level": level("fat_g"),
            "salt_level": level("salt_g"),
            "allergens": ", ".join(analysis.get("allergens", [])),
            "flags": ", ".join(analysis.get("overall_flags", [])),
        }

    def _append_csv(self, entry: dict) -> None:
        file_exists = os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0
        with open(self.filepath, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(entry)

    def _append_json(self, entry: dict) -> None:
        entries = []
        if os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except json.JSONDecodeError:
                entries = []  # corrupt/empty file — start fresh rather than crash
        entries.append(entry)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
