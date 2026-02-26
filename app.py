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

# Full SDMX keys (no string building)
indicators = {
    "Brent Oil ($/bbl)": "G001.POILBRE.A",
    "LNG Asia ($/MMBtu)": "G001.PNGASJP.A",
    "Food & Beverage Index": "G001.PFANDBW.A",
    "Food Price Index": "G001.PFOODW.A",
    "Wheat ($/MT)": "G001.PWHEAMT.A"
}

# ✅ User selects indicators
selected_indicators = st.multiselect(
    "Select Indicators",
    options=list(indicators.keys()),
    default=["Brent Oil ($/bbl)"]
)

if st.button("Retrieve Data"):

    if not selected_indicators:
        st.warning("Please select at least one indicator.")
    else:
        try:
            IMF = sdmx.Client("IMF")
            results = []

            for name in selected_indicators:
                full_key = indicators[name]

                data_msg = IMF.data(
                    resource_id="WEO",
                    key=full_key,
                    params={
                        "startPeriod": str(year),
                        "endPeriod": str(year)
                    }
                )

                df = sdmx.to_pandas(data_msg)

                if df is not None and len(df) > 0:
                    value = float(df.values[0])
                    results.append([name, value])
                else:
                    results.append([name, "No data"])

            final_df = pd.DataFrame(
                results,
                columns=["Indicator", f"Value ({year})"]
            )

            st.success(f"Selected Indicators for {year}")
            st.dataframe(final_df)

            # Optional chart
            numeric_df = final_df[final_df[f"Value ({year})"] != "No data"]
            if not numeric_df.empty:
                st.bar_chart(
                    numeric_df.set_index("Indicator")
                )

        except Exception as e:
            st.error(f"Error: {e}")
