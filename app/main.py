# File structure:
# /app
#   ├── main.py
#   ├── utils/
#   │   ├── __init__.py
#   │   ├── data_loader.py
#   │   ├── optimizer.py
#   │   └── visualization.py
#   └── requirements.txt


# main.py
import streamlit as st
from streamlit_folium import folium_static
from geopy.distance import geodesic
import pandas as pd

from utils.data_loader import load_data
from utils.optimizer import optimize_assignments
from utils.visualization import create_map

def main():
    st.title("Trucks and Cargo Map Visualization with Optimal Assignment")

    # Add sidebar with file uploaders
    with st.sidebar:
        st.header("Upload Data Files")

        st.subheader("Trucks Data")
        trucks_file = st.file_uploader(
            "Upload CSV file with truck positions",
            type=['csv'],
            key='trucks'
        )

        st.subheader("Cargo Data")
        cargo_file = st.file_uploader(
            "Upload CSV file with cargo positions",
            type=['csv'],
            key='cargo'
        )

    # Load data when files are uploaded
    trucks_df = load_data(trucks_file)
    cargo_df = load_data(cargo_file)

    if trucks_df is not None and cargo_df is not None:
        # Show warning if unequal numbers
        if len(trucks_df) != len(cargo_df):
            st.warning(f"Unequal numbers of trucks ({len(trucks_df)}) and cargo ({len(cargo_df)}). "
                       f"Some will remain unassigned.")

        try:
            # Calculate optimized assignments
            assignments = optimize_assignments(trucks_df, cargo_df)

            if assignments:
                display_results(trucks_df, cargo_df, assignments)
            else:
                st.error("No valid assignments could be made.")

        except Exception as e:
            st.error(f"Error during optimization: {str(e)}")
            st.info("Please check your input data and try again.")
    else:
        st.info("Please upload both truck and cargo data files to visualize the map.")

def display_results(trucks_df, cargo_df, assignments):
    """Display optimization results, map, and statistics"""
    # Calculate total distance
    total_distance = sum(
        geodesic(
            (trucks_df.iloc[r]['Latitude'], trucks_df.iloc[r]['Longitude']),
            (cargo_df.iloc[c]['Latitude'], cargo_df.iloc[c]['Longitude'])
        ).kilometers
        for r, c in assignments
    )

    # Display optimization results
    st.subheader("Optimization Results")
    st.metric("Total Distance", f"{total_distance:.2f} km")

    # Create and display assignments table
    display_assignments_table(trucks_df, cargo_df, assignments)

    # Display map
    st.subheader("Map Visualization")
    map_obj = create_map(trucks_df, cargo_df, assignments)
    folium_static(map_obj)

    # Display summary statistics
    display_summary_statistics(trucks_df, cargo_df, assignments, total_distance)

def display_assignments_table(trucks_df, cargo_df, assignments):
    """Create and display the assignments table"""
    assignments_data = []
    for truck_idx, cargo_idx in assignments:
        truck = trucks_df.iloc[truck_idx]
        cargo = cargo_df.iloc[cargo_idx]
        distance = geodesic(
            (truck['Latitude'], truck['Longitude']),
            (cargo['Latitude'], cargo['Longitude'])
        ).kilometers

        assignments_data.append({
            "Truck Location": truck['Address'],
            "Cargo Location": cargo['Address'],
            "Distance (km)": f"{distance:.2f}"
        })

    st.dataframe(pd.DataFrame(assignments_data))

def display_summary_statistics(trucks_df, cargo_df, assignments, total_distance):
    """Display summary statistics in columns"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Number of Trucks", len(trucks_df))
    with col2:
        st.metric("Number of Cargo", len(cargo_df))
    with col3:
        st.metric("Assignments Made", len(assignments))
    with col4:
        avg_distance = total_distance / len(assignments) if assignments else 0
        st.metric("Average Distance", f"{avg_distance:.2f} km")

if __name__ == "__main__":
    main()