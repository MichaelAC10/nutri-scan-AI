"""
suggestions.py

MealSuggestionGenerator: uses Google's Gemini API to turn raw nutrition
analysis into a plain-language explanation, and to suggest healthier
alternatives / recipes using similar ingredients.

Requires a GEMINI_API_KEY environment variable, or a key passed directly.
Install: pip install google-genai
"""

import json
import os

from exceptions import SuggestionGenerationError
from models import FoodProduct


class MealSuggestionGenerator:
    """Wraps Gemini API calls for label explanation + alternatives."""

    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise SuggestionGenerationError(
                "No Gemini API key found. Set the GEMINI_API_KEY environment "
                "variable or pass api_key explicitly."
            )
        self._client = None  # lazy-loaded so the app can start without the SDK installed

    # ---------- Public methods ----------

    def explain_label(self, product: FoodProduct, analysis: dict) -> str:
        """
        Ask Gemini for a short, plain-English explanation of the product's
        nutrition profile, aimed at a non-expert reader.
        """
        prompt = self._build_explanation_prompt(product, analysis)
        try:
            return self._call_gemini(prompt)
        except SuggestionGenerationError:
            raise
        except Exception as exc:
            raise SuggestionGenerationError(f"Failed to generate label explanation: {exc}") from exc

    def suggest_alternatives(self, product: FoodProduct, analysis: dict, max_suggestions: int = 3) -> dict:
        """
        Ask Gemini for healthier alternatives and/or a simple recipe using
        similar ingredients. Returns a dict with 'alternatives' and 'recipe'
        keys. Falls back to a raw-text field if JSON parsing fails.
        """
        prompt = self._build_alternatives_prompt(product, analysis, max_suggestions)
        try:
            raw_text = self._call_gemini(prompt)
        except SuggestionGenerationError:
            raise
        except Exception as exc:
            raise SuggestionGenerationError(f"Failed to generate alternatives: {exc}") from exc

        return self._parse_json_response(raw_text)

    # ---------- Prompt building ----------

    @staticmethod
    def _build_explanation_prompt(product: FoodProduct, analysis: dict) -> str:
        nutrient_lines = []
        for key in ("energy_kcal", "sugar_g", "fat_g", "saturated_fat_g", "salt_g"):
            info = analysis.get(key, {})
            if info.get("value") is not None:
                nutrient_lines.append(f"- {info['label']}: {info['value']} (level: {info['level']})")

        allergen_line = ", ".join(analysis.get("allergens", [])) or "None listed"

        return (
            "You are a friendly nutrition assistant. Explain this food product's "
            "nutrition label in 3-4 simple sentences for someone with no nutrition "
            "background. Mention anything notably high (sugar, salt, fat, calories), "
            "and reassure them about anything that's fine. Avoid jargon.\n\n"
            f"Product: {product.name} ({product.brand})\n"
            f"Nutrition per 100g:\n" + "\n".join(nutrient_lines) + "\n"
            f"Allergens: {allergen_line}\n"
        )

    @staticmethod
    def _build_alternatives_prompt(product: FoodProduct, analysis: dict, max_suggestions: int) -> str:
        flags = ", ".join(analysis.get("overall_flags", [])) or "no major concerns"
        return (
            "You are a nutrition assistant. Based on the product below, suggest "
            f"up to {max_suggestions} healthier alternative products AND one simple "
            "recipe idea that uses similar ingredients but is more nutritious.\n\n"
            f"Product: {product.name}\n"
            f"Ingredients: {product.ingredients_text or 'Not available'}\n"
            f"Nutrition concerns: {flags}\n\n"
            "Respond ONLY with valid JSON (no markdown fences, no preamble) in "
            "exactly this shape:\n"
            '{"alternatives": ["...", "...", "..."], '
            '"recipe": {"title": "...", "description": "...", "ingredients": ["...", "..."]}}'
        )

    # ---------- Gemini call ----------

    def _call_gemini(self, prompt: str) -> str:
        """Lazily import and call the Gemini SDK; wrap all failures."""
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise SuggestionGenerationError(
                    "google-genai package not installed. Run: pip install google-genai"
                ) from exc
            self._client = genai.Client(api_key=self.api_key)

        try:
            response = self._client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
            )
        except Exception as exc:
            raise SuggestionGenerationError(f"Gemini API call failed: {exc}") from exc

        text = getattr(response, "text", None)
        if not text:
            raise SuggestionGenerationError("Gemini returned an empty response.")
        return text.strip()

    # ---------- Response parsing ----------

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict:
        """
        Strip accidental markdown fences and parse JSON. Falls back to
        returning the raw text under 'raw' if parsing fails, rather than
        crashing the whole request.
        """
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1).replace("json", "", 1)

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            return {"alternatives": [], "recipe": None, "raw": raw_text}
