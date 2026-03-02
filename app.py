import streamlit as st
import sdmx
import pandas as pd

st.set_page_config(page_title="Global Macro Dashboard (WEO)", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO)")
st.caption("Source: IMF World Economic Outlook (WEO)")

@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF")

col1, col2 = st.columns(2)

with col1:
    start_year = st.number_input("Start Year", 1980, 2030, 2015)

with col2:
    end_year = st.number_input("End Year", 1980, 2030, 2025)

if end_year < start_year:
    st.error("End year must be greater than Start year.")
    st.stop()

imf_indicators = {
    "World Real GDP Growth (%)": "WLD.NGDP_RPCH",
    "World CPI Inflation (%)": "WLD.PCPIPCH",
    "World Nominal GDP (USD)": "WLD.NGDPD",
    "Current Account (% GDP)": "WLD.BCA_NGDPD"
}

selected = st.multiselect(
    "Select Indicators",
    list(imf_indicators.keys()),
    default=["World Real GDP Growth (%)"]
)

@st.cache_data
def fetch_imf_series(key, start_year, end_year):
    IMF = get_imf_client()

    try:
        data_msg = IMF.data(
            resource_id="WEO",
            key=key,
            params={
                "startPeriod": str(start_year),
                "endPeriod": str(end_year)
            }
        )

        df = sdmx.to_pandas(data_msg)

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

if selected:
    combined = pd.DataFrame()

    for name in selected:
        key = imf_indicators[name]
        series = fetch_imf_series(key, start_year, end_year)

        if series is not None:
            combined = pd.concat([combined, series.rename(name)], axis=1)

    if not combined.empty:
        st.dataframe(combined, width="stretch")
        st.line_chart(combined)
    else:
        st.warning("No data returned.")
