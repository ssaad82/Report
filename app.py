import streamlit as st
import sdmx
import pandas as pd
from fredapi import Fred
import requests

# ------------------------------------------------
# Page Config
# ------------------------------------------------
st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO + FRED + ECB)")
st.caption("Source: IMF WEO, FRED & ECB")

# ------------------------------------------------
# 🔐 FRED API
# ------------------------------------------------
FRED_API_KEY = st.secrets.get("FRED_API_KEY")

if FRED_API_KEY is None:
    st.error("FRED API key missing. Please add it in Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_fred_client():
    return Fred(api_key=FRED_API_KEY)

# ------------------------------------------------
# Year Selection
# ------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    start_year = st.number_input("Start Year", 1980, 2030, 2015)

with col2:
    end_year = st.number_input("End Year", 1980, 2030, 2025)

if end_year < start_year:
    st.error("End year must be greater than Start year.")
    st.stop()

# ------------------------------------------------
# Indicators
# ------------------------------------------------
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

ecb_indicators = {
    "ECB Main Refinancing Operations Rate (Annual Avg %)": "ECB_MRO"
}

# ------------------------------------------------
# Indicator Selection
# ------------------------------------------------
selected_indicators = st.multiselect(
    "Select Indicators",
    list(imf_indicators.keys())
    + list(fred_indicators.keys())
    + list(ecb_indicators.keys()),
    default=["Brent Oil ($/bbl)"]
)

# ------------------------------------------------
# IMF Client
# ------------------------------------------------
@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF_DATA")

# ------------------------------------------------
# Fetch IMF WEO Data
# ------------------------------------------------
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

        df = sdmx.to_pandas(data_msg)

        if df is None or len(df) == 0:
            return None

        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("TIME_PERIOD")

        df = df.squeeze()
        df.index = pd.to_numeric(df.index)
        df = df.dropna()
        df.index = df.index.astype(int)

        return df.sort_index()

    except Exception as e:
        st.error(f"IMF Error: {e}")
        return None

# ------------------------------------------------
# Fetch FRED Data (Year-End Value)
# ------------------------------------------------
@st.cache_data
def fetch_fred_series(series_id, start_year, end_year):

    fred = get_fred_client()

    try:
        df = fred.get_series(
            series_id,
            observation_start=f"{start_year}-01-01",
            observation_end=f"{end_year}-12-31"
        )

        if df.empty:
            return None

        df.index = pd.to_datetime(df.index)

        year_end = df.groupby(df.index.year).last()
        year_end = year_end.loc[start_year:end_year]

        return year_end

    except Exception as e:
        st.error(f"FRED Error: {e}")
        return None

# ------------------------------------------------
# Fetch ECB MRO Rate (Annual Average)
# ------------------------------------------------
@st.cache_data
def fetch_ecb_mro(start_year, end_year):

    try:
        base_url = "https://data-api.ecb.europa.eu/service/data"
        dataset = "FM"
        key = "D.U2.MRR_FR.LEV"

        url = f"{base_url}/{dataset}/{key}"

        params = {
            "startPeriod": f"{start_year}-01-01",
            "endPeriod": f"{end_year}-12-31"
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            st.error(f"ECB API Error: {response.status_code}")
            return None

        data = response.json()

        series = list(data["dataSets"][0]["series"].values())[0]["observations"]
        time_periods = data["structure"]["dimensions"]["observation"][0]["values"]

        dates = []
        values = []

        for idx, val in series.items():
            dates.append(time_periods[int(idx)]["id"])
            values.append(val[0])

        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Value": values
        })

        df["Year"] = df["Date"].dt.year

        annual_avg = df.groupby("Year")["Value"].mean()

        return annual_avg.loc[start_year:end_year]

    except Exception as e:
        st.error(f"ECB Error: {e}")
        return None

# ------------------------------------------------
# Main Logic
# ------------------------------------------------
if selected_indicators:

    combined_df = pd.DataFrame()

    for name in selected_indicators:

        if name in imf_indicators:
            series = fetch_imf_series(imf_indicators[name], start_year, end_year)

        elif name in fred_indicators:
            series = fetch_fred_series(fred_indicators[name], start_year, end_year)

        elif name in ecb_indicators:
            series = fetch_ecb_mro(start_year, end_year)

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

        st.dataframe(combined_df, use_container_width=True)

        st.subheader("📈 Time Series Chart")
        st.line_chart(combined_df)

        st.download_button(
            "📥 Download CSV",
            combined_df.to_csv().encode("utf-8"),
            file_name=f"Macro_data_{start_year}_{end_year}.csv",
            mime="text/csv"
        )

    else:
        st.warning("No data returned.")

else:
    st.info("Select at least one indicator.")
