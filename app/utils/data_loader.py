
# utils/data_loader.py
import streamlit as st
import pandas as pd

def load_data(uploaded_file):
    """
    Load and validate CSV file
    """
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            required_columns = ['Address', 'Latitude', 'Longitude']
            if not all(col in df.columns for col in required_columns):
                st.error(f"File must contain columns: {', '.join(required_columns)}")
                return None
            return df
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
            return None
    return None
