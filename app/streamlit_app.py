import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
import json


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


def calculate_distances(trucks_df, cargo_df):
    """
    Calculate distance matrix between all trucks and cargo locations
    """
    distances = np.zeros((len(trucks_df), len(cargo_df)))
    for i, truck in trucks_df.iterrows():
        for j, cargo in cargo_df.iterrows():
            truck_loc = (truck['Latitude'], truck['Longitude'])
            cargo_loc = (cargo['Latitude'], cargo['Longitude'])
            distances[i, j] = geodesic(truck_loc, cargo_loc).kilometers
    return distances


def optimize_assignments(trucks_df, cargo_df):
    """
    Optimize assignments between trucks and cargo
    Returns list of (truck_idx, cargo_idx) tuples
    """
    distances = calculate_distances(trucks_df, cargo_df)
    num_trucks = len(trucks_df)
    num_cargo = len(cargo_df)

    # Create a square cost matrix
    max_dim = max(num_trucks, num_cargo)
    cost_matrix = np.full((max_dim, max_dim), 1e6)  # Use large value instead of inf
    cost_matrix[:num_trucks, :num_cargo] = distances

    # Solve the assignment problem
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # Filter out dummy assignments
    valid_assignments = []
    for r, c in zip(row_ind, col_ind):
        if r < num_trucks and c < num_cargo:
            valid_assignments.append((r, c))

    return valid_assignments


def create_map(trucks_df, cargo_df, assignments):
    """
    Create a Folium map with trucks, cargo markers and connection lines
    """
    # Calculate the center of all points
    all_lats = pd.concat([trucks_df['Latitude'], cargo_df['Latitude']])
    all_lons = pd.concat([trucks_df['Longitude'], cargo_df['Longitude']])
    center_lat = all_lats.mean()
    center_lon = all_lons.mean()

    # Create the base map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    # Track assigned trucks and cargo
    assigned_trucks = set()
    assigned_cargo = set()

    # Add lines and markers for assigned pairs
    for truck_idx, cargo_idx in assignments:
        assigned_trucks.add(truck_idx)
        assigned_cargo.add(cargo_idx)

        truck = trucks_df.iloc[truck_idx]
        cargo = cargo_df.iloc[cargo_idx]

        # Add truck marker (green for assigned)
        folium.Marker(
            location=[truck['Latitude'], truck['Longitude']],
            popup=f"Truck at: {truck['Address']}<br>Assigned to: {cargo['Address']}",
            icon=folium.Icon(color='green', icon='truck', prefix='fa'),
            tooltip='Assigned Truck'
        ).add_to(m)

        # Add cargo marker (green for assigned)
        folium.Marker(
            location=[cargo['Latitude'], cargo['Longitude']],
            popup=f"Cargo at: {cargo['Address']}<br>Assigned to truck from: {truck['Address']}",
            icon=folium.Icon(color='green', icon='box', prefix='fa'),
            tooltip='Assigned Cargo'
        ).add_to(m)

        # Calculate distance
        distance = geodesic(
            (truck['Latitude'], truck['Longitude']),
            (cargo['Latitude'], cargo['Longitude'])
        ).kilometers

        # Create line with distance tooltip
        points = [
            [truck['Latitude'], truck['Longitude']],
            [cargo['Latitude'], cargo['Longitude']]
        ]

        # Add line with hover effect
        line_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[points[0][1], points[0][0]],
                                [points[1][1], points[1][0]]]
            },
            "properties": {
                "distance": f"{distance:.2f} km",
                "truck": truck['Address'],
                "cargo": cargo['Address']
            }
        }

        folium.GeoJson(
            line_feature,
            style_function=lambda x: {
                'color': 'green',
                'weight': 2,
                'opacity': 0.8
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['distance', 'truck', 'cargo'],
                aliases=['Distance:', 'Truck Location:', 'Cargo Location:'],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
            )
        ).add_to(m)

    # Add unassigned trucks (red markers)
    for idx, truck in trucks_df.iterrows():
        if idx not in assigned_trucks:
            folium.Marker(
                location=[truck['Latitude'], truck['Longitude']],
                popup=f"Unassigned Truck at: {truck['Address']}",
                icon=folium.Icon(color='red', icon='truck', prefix='fa'),
                tooltip='Unassigned Truck'
            ).add_to(m)

    # Add unassigned cargo (red markers)
    for idx, cargo in cargo_df.iterrows():
        if idx not in assigned_cargo:
            folium.Marker(
                location=[cargo['Latitude'], cargo['Longitude']],
                popup=f"Unassigned Cargo at: {cargo['Address']}",
                icon=folium.Icon(color='red', icon='box', prefix='fa'),
                tooltip='Unassigned Cargo'
            ).add_to(m)

    return m


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
                # Calculate total distance for valid assignments
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

                # Create and display detailed assignments table
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

                # Display map
                st.subheader("Map Visualization")
                map_obj = create_map(trucks_df, cargo_df, assignments)
                folium_static(map_obj)

                # Display summary statistics
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
            else:
                st.error("No valid assignments could be made.")

        except Exception as e:
            st.error(f"Error during optimization: {str(e)}")
            st.info("Please check your input data and try again.")
    else:
        st.info("Please upload both truck and cargo data files to visualize the map.")


if __name__ == "__main__":
    main()