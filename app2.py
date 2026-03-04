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
# 🔐 FRED API  (fix #5: check falsy, not just None)
# ------------------------------------------------
FRED_API_KEY = st.secrets.get("FRED_API_KEY")

if not FRED_API_KEY:
    st.error("FRED API key missing or empty. Please add it in Streamlit Secrets.")
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

# Fix #9: guard equal years too (need at least a range for meaningful annual data)
if end_year <= start_year:
    st.error("End year must be strictly greater than Start year.")
    st.stop()

# ------------------------------------------------
# Indicators
# ------------------------------------------------
imf_indicators = {
    "Brent Oil ($/bbl)": "G001.POILBRE.A",
    "LNG Asia ($/MMBtu)": "G001.PNGASJP.A",
    "Wheat ($/MT)": "G001.PWHEAMT.A",
    "Food Price Index": "G001.PFOODW.A",
    "Food & Beverage Index": "G001.PFANDBW.A",
}

fred_indicators = {
    "Effective Fed Funds Rate (Year-End, DFF %)": "DFF",
}

# Fix #10: use a clear sentinel name; actual routing is done below
ecb_indicators = {
    "ECB Main Refinancing Operations Rate (Annual Avg %)": "ECB_MRO",
}

# ------------------------------------------------
# Indicator Selection
# ------------------------------------------------
selected_indicators = st.multiselect(
    "Select Indicators",
    list(imf_indicators.keys()) + list(fred_indicators.keys()) + list(ecb_indicators.keys()),
    default=["Brent Oil ($/bbl)"],
)

# ------------------------------------------------
# IMF Client  (fix #6: instantiated inside cache_data to avoid cross-cache dependency)
# ------------------------------------------------
@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF_DATA")

# ------------------------------------------------
# Fetch IMF WEO Data
# ------------------------------------------------
@st.cache_data
def fetch_imf_series(full_key: str, start_year: int, end_year: int) -> pd.Series | None:
    IMF = get_imf_client()
    try:
        data_msg = IMF.data(
            resource_id="WEO",
            key=full_key,
            params={"startPeriod": str(start_year), "endPeriod": str(end_year)},
        )

        df = sdmx.to_pandas(data_msg)

        if df is None or len(df) == 0:
            return None

        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("TIME_PERIOD")

        # Fix #2: explicit first-column extraction instead of fragile squeeze()
        if isinstance(df, pd.DataFrame):
            df = df.iloc[:, 0]

        df = df.squeeze()
        df.index = pd.to_numeric(df.index, errors="coerce")
        df = df.dropna()
        df.index = df.index.astype(int)

        # Fix #1 (IMF variant): boolean mask instead of .loc[] label slicing
        df = df.sort_index()
        return df[(df.index >= start_year) & (df.index <= end_year)]

    except Exception as e:
        st.error(f"IMF Error: {e}")
        return None

# ------------------------------------------------
# Fetch FRED Data (Year-End Value)
# ------------------------------------------------
@st.cache_data
def fetch_fred_series(series_id: str, start_year: int, end_year: int) -> pd.Series | None:
    fred = get_fred_client()
    try:
        df = fred.get_series(
            series_id,
            observation_start=f"{start_year}-01-01",
            observation_end=f"{end_year}-12-31",
        )

        if df.empty:
            return None

        df.index = pd.to_datetime(df.index)
        year_end = df.groupby(df.index.year).last()

        # Fix #1: boolean mask instead of .loc[] label slicing
        return year_end[(year_end.index >= start_year) & (year_end.index <= end_year)]

    except Exception as e:
        st.error(f"FRED Error: {e}")
        return None

# ------------------------------------------------
# Fetch ECB MRO Rate (Annual Average)
# ------------------------------------------------
@st.cache_data
def fetch_ecb_mro(start_year: int, end_year: int) -> pd.Series | None:
    try:
        url = "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.4F.KR.MRR_FR.LEV"
        params = {
            "startPeriod": str(start_year),
            "endPeriod": str(end_year),
            "format": "jsondata",
        }
        # Fix #4: added timeout so the app doesn't hang indefinitely
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/vnd.sdmx.data+json"},
            timeout=10,
        )
        response.raise_for_status()  # raises HTTPError for 4xx/5xx

        data = response.json()
        series = list(data["dataSets"][0]["series"].values())[0]["observations"]
        time_periods = data["structure"]["dimensions"]["observation"][0]["values"]

        years, values = [], []
        for idx, val in series.items():
            period_id = time_periods[int(idx)]["id"]      # e.g. "2023-01"
            year = int(period_id.split("-")[0])            # fix: safer than [:4]
            years.append(year)
            values.append(val[0])

        df = pd.Series(values, index=years)
        df = df.groupby(df.index).mean().sort_index()

        # Fix #1: boolean mask instead of .loc[] label slicing
        return df[(df.index >= start_year) & (df.index <= end_year)]

    except requests.HTTPError as e:
        st.error(f"ECB API Error: {e.response.status_code}")
        return None
    except Exception as e:
        st.error(f"ECB Error: {e}")
        return None

# ------------------------------------------------
# Main Logic
# ------------------------------------------------
if selected_indicators:

    # Fix #11: collect series first, concat once at the end
    series_list = []

    for name in selected_indicators:
        with st.spinner(f"Fetching {name}..."):   # Fix #7: loading spinners
            if name in imf_indicators:
                series = fetch_imf_series(imf_indicators[name], start_year, end_year)

            elif name in fred_indicators:
                series = fetch_fred_series(fred_indicators[name], start_year, end_year)

            elif name in ecb_indicators:
                series = fetch_ecb_mro(start_year, end_year)

            else:
                series = None

        if series is not None:
            series_list.append(series.rename(name))

    if series_list:
        # Fix #11: single concat; fix #3: enforce int index
        combined_df = pd.concat(series_list, axis=1)
        combined_df.index = combined_df.index.astype(int)
        combined_df = combined_df.sort_index()

        st.success(f"Time Series from {start_year} to {end_year}")
        st.dataframe(combined_df, use_container_width=True)

        # Fix #8: normalised chart toggle when mixing different-scale series
        st.subheader("📈 Time Series Chart")

        if len(series_list) > 1:
            normalise = st.toggle("Normalise series (index = 100 at first observation)", value=False)
            if normalise:
                chart_df = combined_df.div(combined_df.iloc[0]).mul(100)
                st.caption("All series rebased to 100 at first available observation.")
            else:
                chart_df = combined_df
        else:
            chart_df = combined_df

        st.line_chart(chart_df)

        st.download_button(
            "📥 Download CSV",
            combined_df.to_csv().encode("utf-8"),
            file_name=f"Macro_data_{start_year}_{end_year}.csv",
            mime="text/csv",
        )

    else:
        st.warning("No data returned for the selected indicators and date range.")

else:
    st.info("Select at least one indicator.")
