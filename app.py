import streamlit as st
import sdmx
import pandas as pd
from fredapi import Fred

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF Commodities + FRED)")
st.caption("Source: IMF Primary Commodity Prices (PCPS) & FRED")

# -------------------------
# 🔐 FRED API
# -------------------------
# For production:
# FRED_API_KEY = st.secrets["FRED_API_KEY"]
FRED_API_KEY = "YOUR_FRED_API_KEY"

@st.cache_resource
def get_fred_client():
    return Fred(api_key=FRED_API_KEY)

# -------------------------
# Year Range
# -------------------------
col1, col2 = st.columns(2)

with col1:
    start_year = st.number_input("Start Year", 1980, 2030, 2015)

with col2:
    end_year = st.number_input("End Year", 1980, 2030, 2025)

if end_year < start_year:
    st.error("End year must be greater than Start year.")
    st.stop()

# -------------------------
# IMF Commodity Indicators (PCPS DATAFLOW)
# -------------------------
imf_indicators = {
    "Brent Oil ($/bbl)": "G001.POILBRE.A",
    "LNG Asia ($/MMBtu)": "G001.PNGASJP.A",
    "Wheat ($/MT)": "G001.PWHEAMT.A",
    "Food Price Index": "G001.PFOODW.A",
    "Food & Beverage Index": "G001.PFANDBW.A"
}

fred_indicators = {
    "Effective Fed Funds Rate (Year-End, DFF %)": "DFF"
}

selected_indicators = st.multiselect(
    "Select Indicators",
    options=list(imf_indicators.keys()) + list(fred_indicators.keys()),
    default=["Brent Oil ($/bbl)"]
)

# -------------------------
# IMF Client
# -------------------------
@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF")

# -------------------------
# Fetch IMF Commodity Data
# -------------------------
@st.cache_data
def fetch_imf_series(key, start_year, end_year):

    IMF = get_imf_client()

    try:
        data_msg = IMF.data(
            resource_id="PCPS",  # IMPORTANT CHANGE
            key=key,
            params={
                "startPeriod": str(start_year),
                "endPeriod": str(end_year)
            }
        )

        df = sdmx.to_pandas(data_msg)

        if df is None or len(df) == 0:
            return None

        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("TIME_PERIOD")

        df = df.squeeze()
        df.index = pd.to_numeric(df.index, errors="coerce")
        df = df.dropna()
        df.index = df.index.astype(int)
        df = df.sort_index()

        return df

    except Exception as e:
        st.error(f"IMF Error: {e}")
        return None

# -------------------------
# Fetch FRED Data
# -------------------------
@st.cache_data
def fetch_fred_series(series_id, start_year, end_year):

    fred = get_fred_client()

    try:
        df = fred.get_series(
            series_id,
            observation_start=f"{start_year}-01-01",
            observation_end=f"{end_year}-12-31"
        )

        df = df.to_frame(name="value")
        df_year_end = df.resample("YE").last()
        df_year_end.index = df_year_end.index.year

        return df_year_end["value"]

    except Exception as e:
        st.error(f"FRED Error: {e}")
        return None

# -------------------------
# Main Logic
# -------------------------
if selected_indicators:

    combined_df = pd.DataFrame()

    for name in selected_indicators:

        if name in imf_indicators:
            key = imf_indicators[name]
            series = fetch_imf_series(key, start_year, end_year)

        elif name in fred_indicators:
            series_id = fred_indicators[name]
            series = fetch_fred_series(series_id, start_year, end_year)

        else:
            series = None

        if series is not None:
            combined_df = pd.concat(
                [combined_df, series.rename(name)],
                axis=1
            )

    if not combined_df.empty:

        combined_df = combined_df.sort_index()

        st.success(f"Time Series from {start_year} to {end_year}")

        st.dataframe(combined_df, width="stretch")

        st.subheader("📈 Time Series Chart")
        st.line_chart(combined_df)

        csv = combined_df.to_csv().encode("utf-8")

        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"Macro_data_{start_year}_{end_year}.csv",
            mime="text/csv"
        )

    else:
        st.warning("No data returned. Check dataset or years.")

else:
    st.info("Select at least one indicator.")
