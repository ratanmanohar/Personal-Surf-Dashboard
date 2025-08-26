import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px

st.title("Test App")
st.write("If you see this, basic imports work")

# Test API call
try:
    response = requests.get("https://api.open-meteo.com/v1/forecast?latitude=32.75&longitude=-117.25&hourly=temperature_2m")
    if response.status_code == 200:
        st.success("API call successful")
    else:
        st.error(f"API call failed: {response.status_code}")
except Exception as e:
    st.error(f"Error: {e}")