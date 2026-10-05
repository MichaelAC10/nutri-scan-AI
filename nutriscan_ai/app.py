"""
app.py

NutriScan AI — Streamlit front end.
Run with: streamlit run app.py
"""

import os

import pandas as pd
import streamlit as st

from analyzer import NutritionAnalyzer
from exceptions import (
    APIRequestError,
    FoodLogError,
    IncompleteDataError,
    InvalidBarcodeError,
    NutriScanError,
    ProductNotFoundError,
    SuggestionGenerationError,
)
from food_logger import FoodLogger
from off_client import OpenFoodFactsClient
from suggestions import MealSuggestionGenerator

st.set_page_config(page_title="NutriScan AI", page_icon="🥗", layout="centered")

LOG_PATH = "food_log.csv"

# ---------- Cached resources ----------


@st.cache_resource
def get_client() -> OpenFoodFactsClient:
    return OpenFoodFactsClient()


@st.cache_resource
def get_logger() -> FoodLogger:
    return FoodLogger(LOG_PATH)


def get_suggestion_generator():
    """Not cached at resource level since the key can change per session."""
    api_key = st.session_state.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return MealSuggestionGenerator(api_key=api_key)
    except SuggestionGenerationError:
        return None


# ---------- Sidebar: settings ----------

with st.sidebar:
    st.header("⚙️ Settings")
    key_input = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.get("gemini_api_key", ""),
        help="Needed for AI label explanations and alternative suggestions.",
    )
    if key_input:
        st.session_state["gemini_api_key"] = key_input

    st.divider()
    st.header("📒 Food Log")
    if st.button("View log"):
        st.session_state["show_log"] = True


# ---------- Header ----------

st.title("🥗 NutriScan AI")
st.caption("Scan a product, understand the label, eat smarter.")

tab_search, tab_log = st.tabs(["🔍 Scan a Product", "📒 Food Log"])

# ============================================================
# TAB 1 — SEARCH / SCAN
# ============================================================
with tab_search:
    mode = st.radio("Search by:", ["Product name", "Barcode"], horizontal=True)
    query = st.text_input("Enter product name or barcode" if mode == "Product name" else "Enter barcode number")
    search_clicked = st.button("Search", type="primary")

    if search_clicked and query.strip():
        client = get_client()
        products = []

        with st.spinner("Fetching product data..."):
            try:
                if mode == "Barcode":
                    products = [client.get_by_barcode(query)]
                else:
                    products = client.search_by_name(query)
            except InvalidBarcodeError as e:
                st.error(f"❌ Invalid barcode: {e}")
            except ProductNotFoundError as e:
                st.warning(f"⚠️ {e}")
            except APIRequestError as e:
                st.error(f"🌐 Network/API error: {e}")
            except NutriScanError as e:
                st.error(f"⚠️ {e}")

        if products:
            st.session_state["last_results"] = products

    # ---------- Display results ----------
    results = st.session_state.get("last_results", [])
    if results:
        names = [f"{p.name} — {p.brand}" if p.brand else p.name for p in results]
        idx = 0
        if len(results) > 1:
            idx = st.selectbox("Select a product", range(len(results)), format_func=lambda i: names[i])
        product = results[idx]

        st.subheader(product.name)
        if product.brand:
            st.caption(f"Brand: {product.brand}")
        if product.image_url:
            st.image(product.image_url, width=200)

        if product.ingredients_text:
            with st.expander("📋 Ingredients"):
                st.write(product.ingredients_text)

        # ---------- Nutrition analysis ----------
        try:
            analysis = NutritionAnalyzer(product).analyze()
        except IncompleteDataError as e:
            st.warning(f"⚠️ {e}")
            analysis = None

        if analysis:
            st.subheader("📊 Nutrition Breakdown (per 100g)")
            level_emoji = {"Low": "🟢", "Moderate": "🟡", "High": "🔴", "Unknown": "⚪"}

            cols = st.columns(3)
            display_keys = ["energy_kcal", "sugar_g", "fat_g", "saturated_fat_g", "salt_g"]
            for i, key in enumerate(display_keys):
                info = analysis[key]
                with cols[i % 3]:
                    value_str = f"{info['value']}" if info["value"] is not None else "N/A"
                    st.metric(
                        label=f"{level_emoji.get(info['level'], '⚪')} {info['label']}",
                        value=value_str,
                        delta=info["level"],
                        delta_color="off",
                    )

            if analysis["overall_flags"]:
                st.warning("**Flags:** " + ", ".join(analysis["overall_flags"]))
            else:
                st.success("No major nutrition red flags at these levels.")

            if analysis["allergens"]:
                st.error("**⚠️ Possible allergens:** " + ", ".join(analysis["allergens"]))
            else:
                st.caption("No allergens listed (data may be incomplete — always check the physical label).")

            # ---------- AI explanation + alternatives ----------
            st.divider()
            st.subheader("🤖 AI Insights")
            generator = get_suggestion_generator()

            if generator is None:
                st.info("Add your Gemini API key in the sidebar to unlock AI explanations and alternatives.")
            else:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Explain this label"):
                        with st.spinner("Asking Gemini..."):
                            try:
                                explanation = generator.explain_label(product, analysis)
                                st.session_state["explanation"] = explanation
                            except SuggestionGenerationError as e:
                                st.error(f"❌ {e}")
                with col_b:
                    if st.button("Suggest healthier options"):
                        with st.spinner("Asking Gemini..."):
                            try:
                                alt = generator.suggest_alternatives(product, analysis)
                                st.session_state["alternatives"] = alt
                            except SuggestionGenerationError as e:
                                st.error(f"❌ {e}")

                if st.session_state.get("explanation"):
                    st.info(st.session_state["explanation"])

                if st.session_state.get("alternatives"):
                    alt = st.session_state["alternatives"]
                    if alt.get("alternatives"):
                        st.write("**Healthier alternatives:**")
                        for item in alt["alternatives"]:
                            st.write(f"- {item}")
                    recipe = alt.get("recipe")
                    if recipe:
                        with st.expander(f"🍳 Recipe idea: {recipe.get('title', 'Suggestion')}"):
                            st.write(recipe.get("description", ""))
                            for ing in recipe.get("ingredients", []):
                                st.write(f"- {ing}")
                    if alt.get("raw") and not alt.get("alternatives"):
                        st.write(alt["raw"])

            # ---------- Save to log ----------
            st.divider()
            if st.button("💾 Save to food log"):
                try:
                    get_logger().save_entry(product, analysis)
                    st.success("Saved to your food log!")
                except FoodLogError as e:
                    st.error(f"❌ {e}")

# ============================================================
# TAB 2 — FOOD LOG
# ============================================================
with tab_log:
    st.subheader("Your Food Log")
    try:
        entries = get_logger().load_log()
    except FoodLogError as e:
        st.error(f"❌ {e}")
        entries = []

    if not entries:
        st.info("No saved products yet. Scan something and hit 'Save to food log'.")
    else:
        df = pd.DataFrame(entries)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download as CSV",
                data=df.to_csv(index=False),
                file_name="food_log_export.csv",
                mime="text/csv",
            )
        with col2:
            st.download_button(
                "⬇️ Download as JSON",
                data=df.to_json(orient="records", indent=2),
                file_name="food_log_export.json",
                mime="application/json",
            )
