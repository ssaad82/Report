import streamlit as st
import sdmx
import pandas as pd

st.title("🌍 Global Macro Dashboard (IMF WEO)")
st.write("Source: IMF World Economic Outlook")

year = st.number_input(
    "Enter Year",
    min_value=1980,
    max_value=2030,
    value=2025,
    step=1
)

if st.button("Retrieve Data"):

    try:
        IMF = sdmx.Client("IMF")

        indicators = {
            "Real GDP Growth (%)": "NGDP_RPCH",
            "Inflation (CPI, %)": "PCPIPCH",
            "Brent Oil ($/bbl)": "POILBRE",
            "LNG Asia ($/MMBtu)": "PNGASJP",
            "Food & Beverage Index": "PFOODBEV",
            "Food Price Index": "PFOOD",
            "Wheat ($/MT)": "PWHEAMT"
        }

        results = []

        for name, code in indicators.items():
            data_msg = IMF.data(
                resource_id="WEO",
                key=f"G001.{code}.A",
                params={
                    "startPeriod": str(year),
                    "endPeriod": str(year)
                }
            )

            df = sdmx.to_pandas(data_msg)

            if not df.empty:
                value = df.values[0]
                results.append([name, value])
            else:
                results.append([name, "No data"])

        final_df = pd.DataFrame(results, columns=["Indicator", f"Value ({year})"])

        st.success(f"Global Indicators for {year}")
        st.dataframe(final_df)

    except Exception as e:
        st.error(f"Error: {e}")
