import streamlit as st
import pandas as pd
import sdmx

st.set_page_config(page_title="IMF Data Dashboard", layout="wide")

st.title("IMF Data Dashboard (SDMX)")

# ---------------------------------------
# IMF Client
# ---------------------------------------
IMF_DATA = sdmx.Client("IMF_DATA")


# ---------------------------------------
# Data Fetch Function
# ---------------------------------------
@st.cache_data
def fetch_time_series(dataset, key, start_year, end_year):

    try:
        data_msg = IMF_DATA.data(
            dataset,
            key=key,
            params={
                "startPeriod": str(start_year),
                "endPeriod": str(end_year)
            }
        )

        df = data_msg.to_pandas()

        if df is None or len(df) == 0:
            return None

        # If Series
        if isinstance(df, pd.Series):

            # Fix MultiIndex (VERY IMPORTANT)
            if isinstance(df.index, pd.MultiIndex):
                df.index = df.index.get_level_values(-1)

            # Convert to datetime safely
            df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.dropna()
            df.index = df.index.year

            return df.sort_index()

        # If DataFrame
        elif isinstance(df, pd.DataFrame):

            if isinstance(df.index, pd.MultiIndex):
                df.index = df.index.get_level_values(-1)

            df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.dropna()
            df.index = df.index.year

            return df.sort_index()

        return None

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None


# ---------------------------------------
# Example Indicators (WEO Dataset)
# ---------------------------------------
indicators = {
    "Brent Crude Oil ($ per barrel)": "G001.POILBRE.A",
    "Real GDP Growth (%) - World": "G001.NGDP_RPCH.A",
    "Inflation (%) - World": "G001.PCPIPCH.A"
}

dataset = "WEO"

# ---------------------------------------
# Sidebar Controls
# ---------------------------------------
st.sidebar.header("Settings")

selected_indicators = st.sidebar.multiselect(
    "Select Indicators",
    list(indicators.keys()),
    default=["Brent Crude Oil ($ per barrel)"]
)

start_year = st.sidebar.number_input("Start Year", value=2015)
end_year = st.sidebar.number_input("End Year", value=2025)

# ---------------------------------------
# Fetch and Display Data
# ---------------------------------------
combined_df = pd.DataFrame()

for name in selected_indicators:
    full_key = indicators[name]

    series = fetch_time_series(dataset, full_key, start_year, end_year)

    if series is not None:
        combined_df[name] = series


# ---------------------------------------
# Output
# ---------------------------------------
if not combined_df.empty:

    st.subheader("Data Table")
    st.dataframe(combined_df)

    st.subheader("Chart")
    st.line_chart(combined_df)

else:
    st.warning("No data returned. Check dataset or years.")
