import streamlit as st
import sdmx
import pandas as pd

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO)")
st.caption("Source: IMF World Economic Outlook (WEO)")

# ---- Year Range ----
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

# ---- Indicators ----
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
    return sdmx.Client("IMF_DATA")

# ---- Fetch Time Series ----
@st.cache_data
def fetch_time_series(full_key, start_year, end_year):

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

        # Flatten MultiIndex if necessary
        if isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("TIME_PERIOD")

        if isinstance(df, pd.DataFrame):
            df = df.squeeze()

        df.index = df.index.astype(int)
        df = df.sort_index()

        return df

    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None


# ---- Main Logic ----
if selected_indicators:

    combined_df = pd.DataFrame()

    for name in selected_indicators:
        full_key = indicators[name]
        series = fetch_time_series(full_key, start_year, end_year)

        if series is not None:
            combined_df[name] = series

    if not combined_df.empty:

        combined_df = combined_df.sort_index()

        st.success(f"Time Series from {start_year} to {end_year}")

        st.dataframe(combined_df, use_container_width=True)

        st.subheader("📈 Time Series Chart")
        st.line_chart(combined_df)

        # ---- Download Button ----
        csv = combined_df.to_csv().encode("utf-8")

        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"IMF_WEO_data_{start_year}_{end_year}.csv",
            mime="text/csv"
        )

    else:
        st.warning("No data returned. Check dataset or years.")

else:
    st.info("Select at least one indicator to display data.")
