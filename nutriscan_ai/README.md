# NutriScan AI

Search a food product by **name** or **barcode**, get its nutrition facts
explained in plain English by AI, see possible allergens, get healthier
alternatives/recipe ideas, and save scanned products to a personal food log.

## Features
- Product lookup via Open Food Facts (name or barcode)
- Nutrition classification (Low / Moderate / High for sugar, fat, saturated fat, salt, calories)
- AI-generated plain-language label explanation (Gemini)
- AI-suggested healthier alternatives + a recipe idea (Gemini)
- Allergen flagging (from available product data)
- Food log saved locally as CSV or JSON, viewable and exportable in-app

## Project Structure
```
nutriscan_ai/
├── app.py              # Streamlit UI (entry point)
├── models.py            # FoodProduct data class + regex helpers
├── off_client.py         # OpenFoodFactsClient — API calls
├── analyzer.py           # NutritionAnalyzer — classification logic
├── suggestions.py         # MealSuggestionGenerator — Gemini API calls
├── food_logger.py         # FoodLogger — CSV/JSON persistence
├── exceptions.py          # Custom exception classes
├── requirements.txt
└── README.md
```

## Setup

1. **Install dependencies** (Python 3.9+):
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a Gemini API key** (free tier available):
   https://aistudio.google.com/apikey

3. **Set your API key** — either:
   - Environment variable (recommended):
     ```bash
     export GEMINI_API_KEY="your-key-here"      # macOS/Linux
     setx GEMINI_API_KEY "your-key-here"         # Windows
     ```
   - Or paste it into the sidebar text field when the app is running (session only).

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   The app opens in your browser at `http://localhost:8501`.

## Usage
1. Choose "Product name" or "Barcode" and search.
2. Review the nutrition breakdown and any allergen warnings.
3. Click "Explain this label" for an AI plain-English summary.
4. Click "Suggest healthier options" for alternatives + a recipe idea.
5. Click "Save to food log" to record the product with a timestamp.
6. Switch to the "Food Log" tab to view history and export as CSV/JSON.

## Notes on the Open Food Facts API
No API key is required. It's a free, community-maintained database, so:
- Barcode lookups are usually reliable for well-known products.
- Name searches can return incomplete data for niche/regional products —
  the app detects this (`IncompleteDataError`) and tells you rather than
  showing wrong numbers.

## Barcode formats accepted
8, 12, 13, or 14 digit numeric codes (EAN-8, UPC-A, EAN-13, ITF-14).
Spaces and hyphens are stripped automatically before validation.

## Error handling summary
| Situation | Behavior |
|---|---|
| Malformed barcode | Caught by regex before any API call — instant feedback |
| Product not found | Friendly message, suggests trying the other search mode |
| API timeout / connection error | Clear network error message, no crash |
| Missing nutrition fields | Product still shown; analysis flags what's missing |
| Gemini call fails / no key | AI section shows a helpful prompt instead of crashing |
| Log file missing or corrupt JSON | Treated as an empty log rather than raising |

## Extending the project
- Swap Streamlit for Tkinter by reusing `models.py`, `off_client.py`,
  `analyzer.py`, `suggestions.py`, and `food_logger.py` unchanged — only
  `app.py` is UI-specific.
- Add camera-based barcode scanning with `opencv-python` + `pyzbar`.
- Add a personal daily-limits profile to compare against `NutritionAnalyzer` thresholds.
