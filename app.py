import streamlit as st
import sdmx
import pandas as pd
from fredapi import Fred

st.set_page_config(page_title="Global Macro Dashboard", layout="wide")

st.title("🌍 Global Macro Dashboard (IMF WEO + FRED)")
st.caption("Source: IMF WEO & FRED (Federal Reserve)")

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

        if df.empty:
            return None

        # Ensure datetime index
        df.index = pd.to_datetime(df.index)

        # Get last available observation of each year
        year_end_values = df.groupby(df.index.year).last()

        # Keep only requested range
        year_end_values = year_end_values.loc[start_year:end_year]

        return year_end_values

    except Exception as e:
        st.error(f"FRED Error: {e}")
        return None

# -------------------------
# IMF Client
# -------------------------
@st.cache_resource
def get_imf_client():
    return sdmx.Client("IMF_DATA")


# -------------------------
# Fetch IMF Data
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

        df.index = df.index.astype(int)
        df = df.sort_index()

        return df

    except Exception as e:
        st.error(f"IMF Error: {e}")
        return None


# -------------------------
# Fetch FRED Data (Exact Date)
# -------------------------
@st.cache_data
def fetch_fred_series(series_id, start_year, end_year):

    fred = get_fred_client()

    try:
        # If Effective Fed Funds Rate selected,
        # get value specifically on 31 December of end_year
        if series_id == "EFFR":
            target_date = f"{end_year}-12-31"

            value = fred.get_series(
                series_id,
                observation_start=target_date,
                observation_end=target_date
            )

            if value.empty:
                st.warning(f"No data available on {target_date}")
                return None

            value.index = [end_year]  # show as year in table
            return value

        else:
            # keep annual logic for other FRED series (if any)
            df = fred.get_series(
                series_id,
                observation_start=f"{start_year}-01-01",
                observation_end=f"{end_year}-12-31"
            )

            df = df.resample("Y").mean()
            df.index = df.index.year
            return df

    except Exception as e:
        st.error(f"FRED Error: {e}")
        return None

# -------------------------
# Main Logic
# -------------------------
if selected_indicators:

    combined_df = pd.DataFrame()

    for name in selected_indicators:

        if name in indicators:
            full_key = indicators[name]
            series = fetch_imf_series(full_key, start_year, end_year)

        elif name in fred_indicators:
            series_id = fred_indicators[name]
            series = fetch_fred_series(series_id, start_year, end_year)

        if series is not None:
            combined_df[name] = series

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
