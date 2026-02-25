import streamlit as st
import sdmx

st.title("IMF Brent Crude Oil Price")
st.write("Source: IMF WEO Dataset")

year = st.number_input(
    "Enter Year",
    min_value=1980,
    max_value=2030,
    value=2025,
    step=1
)

if st.button("Retrieve Data"):

    try:
        IMF_DATA = sdmx.Client('IMF_DATA')

        data_msg = IMF_DATA.data(
            'WEO',
            key='G001.POILBRE.A',
            params={
                'startPeriod': year,
                'endPeriod': year
            }
        )

        df = sdmx.to_pandas(data_msg)

        if df.empty:
            st.warning("No data available.")
        else:
            st.success(f"Brent Price for {year}")
            st.dataframe(df)

    except Exception as e:
        st.error(f"Error: {e}")
