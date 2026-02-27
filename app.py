import streamlit as st
import sdmx
import pandas as pd
from fredapi import Fred

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO + FRED)")
st.caption("Source: IMF WEO & FRED (Federal Reserve)")

# -------------------------
# 🔐 FRED API
# -------------------------
# ⚠️ For production use: st.secrets["FRED_API_KEY"]
FRED_API_KEY = "YOUR_API_KEY_HERE"

@st.cache_resource
def get_fred_client():
    return Fred(api_key=FRED_API_KEY)


# -------------------------
# ---- Year Range ----
# -------------------------
col1, col2 = st.columns(2)

with col1:
    start_year = st.number_input(
        "Start Year",
        min_value=1980,
        max_value=2030,
        value=2015,
        step=1
    )

with col2:
    end_year = st.number_input(
        "End Year",
        min_value=1980,
        max_value=2030,
        value=2025,
        step=1
    )

# -------------------------
# ---- Indicators ----
# -------------------------
imf_indicators = {
    "Brent Oil ($/bbl)": "WEO.WLD.POILBRE.A",
    "LNG Asia ($/MMBtu)": "WEO.WLD.PNGASJP.A",
    "Food & Beverage Index": "WEO.WLD.PFANDBW.A",
    "Food Price Index": "WEO.WLD.PFOODW.A",
    "Wheat ($/MT)": "WEO.WLD.PWHEAMT.A"
}

fred_indicators = {
    "Effective Fed Funds Rate (Year-End %)": "EFFR"
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
    return sdmx.Client("IMF_DATA")


# -------------------------
# Fetch IMF Data (Annual)
# -------------------------
@st.cache_data
def fetch_imf_series(full_key, start_year, end_year):

    IMF = get_imf_client()

    try:
        data_msg = IMF.data(
            resource_id="WEO",
            key=full_key,
            params={
                "startPeriod": str(start_year),
                "endPeriod": str(end_year)
            }
        )

        dataset = data_msg.data[0]
        df = sdmx.to_pandas(dataset)

        if df is None or len(df) == 0:
            return None

        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("TIME_PERIOD")

        if isinstance(df, pd.DataFrame):
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
# Fetch FRED Data (Year-End Value)
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

        # Take last available value of each year (Dec 31 or last business day)
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
            full_key = imf_indicators[name]
            series = fetch_imf_series(full_key, start_year, end_year)

        elif name in fred_indicators:
            series_id = fred_indicators[name]
            series = fetch_fred_series(series_id, start_year, end_year)

        if series is not None:
            combined_df = pd.concat(
                [combined_df, series.rename(name)],
                axis=1
            )

    if not combined_df.empty:

        combined_df = combined_df.sort_index()

        st.success(f"Time Series from {start_year} to {end_year}")

        st.dataframe(combined_df, use_container_width=True)

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
    st.info("Select at least one indicator to display data.")
