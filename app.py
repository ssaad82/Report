import streamlit as st
import sdmx
import pandas as pd

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO)")
st.caption("Source: IMF World Economic Outlook (WEO)")

year = st.number_input(
    "Select Year",
    min_value=1980,
    max_value=2030,
    value=2025,
    step=1
)

# ---- Full SDMX Keys ----
indicators = {
    "Brent Oil ($/bbl)": "G001.POILBRE.A",
    "LNG Asia ($/MMBtu)": "G001.PNGASJP.A",
    "Food & Beverage Index": "G001.PFANDBW.A",
    "Food Price Index": "G001.PFOODW.A",
    "Wheat ($/MT)": "G001.PWHEAMT.A"
}

selected_indicators = st.multiselect(
    "Select Indicators",
    options=list(indicators.keys()),
    default=["Brent Oil ($/bbl)"]
)

# ---- Cache IMF Client ----
@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF_DATA")  # ✅ Important Fix

# ---- Fetch Data ----
@st.cache_data
def fetch_data(full_key, year):
    IMF = get_imf_client()

    data_msg = IMF.data(
        resource_id="WEO",
        key=full_key,
        params={
            "startPeriod": str(year),
            "endPeriod": str(year)
        }
    )

    df = sdmx.to_pandas(data_msg)

    if df is None or len(df) == 0:
        return None

    return float(df.squeeze())


if selected_indicators:

    results = []

    for name in selected_indicators:
        full_key = indicators[name]
        value = fetch_data(full_key, year)

        if value is not None:
            results.append([name, value])
        else:
            results.append([name, "No data"])

    final_df = pd.DataFrame(
        results,
        columns=["Indicator", f"Value ({year})"]
    )

    st.success(f"Selected Indicators for {year}")
    st.dataframe(final_df, use_container_width=True)

    # ---- Chart ----
    numeric_df = final_df[pd.to_numeric(
        final_df[f"Value ({year})"], errors="coerce"
    ).notnull()]

    if not numeric_df.empty:
        st.subheader("Visualization")
        st.bar_chart(numeric_df.set_index("Indicator"))

else:
    st.info("Select at least one indicator to display data.")
