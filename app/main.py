import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_folium import folium_static
from geopy.distance import geodesic

from utils.data_loader import load_data
from utils.time_cost_calculator import optimize_assignments
from utils.visualization import create_map
from utils.time_cost_calculator import TimeCostCalculator, calculate_total_metrics


def show_welcome_message():
    """Display welcome message and instructions"""
    st.markdown("""
    ## 👋 Welcome to the Truck-Cargo Assignment Optimizer!

    This application helps optimize the assignment of trucks to cargo loads by:
    - Minimizing total costs (distance + waiting time)
    - Respecting time windows for pickup and delivery
    - Matching truck and cargo types

    ### 📝 How to use:
    1. Upload your trucks and cargo CSV files using the sidebar
    2. Review the optimization results
    3. Explore the interactive map visualization
    4. Export the results if needed

    ### 📄 Required file formats:

    **Trucks CSV:**
    - truck_id
    - truck type
    - Address (drop off)
    - Latitude (dropoff)
    - Longitude (dropoff)
    - Timestamp (dropoff)
    - avg moving speed, km/h
    - price per km, Eur
    - waiting time price per h, EUR

    **Cargo CSV:**
    - Origin
    - Origin_Latitude
    - Origin_Longitude
    - Available_From
    - Available_To
    - Delivery_Location
    - Delivery_Latitude
    - Delivery_Longitude
    - Cargo_Type
    """)


def format_time(timestamp):
    """Format timestamp for display"""
    try:
        return pd.to_datetime(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp


def main():
    st.set_page_config(
        page_title="Truck-Cargo Assignment Optimizer",
        page_icon="🚚",
        layout="wide"
    )

    st.title("🚚 Truck and Cargo Assignment Optimizer")

    # Add sidebar with file uploaders and options
    with st.sidebar:
        st.header("📂 Upload Data Files")

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

        st.markdown("---")

        # Add optimization settings
        st.header("⚙️ Settings")
        standard_speed = st.number_input(
            "Standard Speed (km/h)",
            value=73,
            min_value=1,
            help="Speed used for travel time calculations"
        )

        show_debug = st.checkbox(
            "Show Debug Information",
            value=False,
            help="Display additional debug information"
        )

    # Load and validate data
    if trucks_file is not None and cargo_file is not None:
        try:
            trucks_df = pd.read_csv(trucks_file)
            cargo_df = pd.read_csv(cargo_file)

            # Data validation
            required_truck_columns = [
                'truck_id', 'truck type', 'Address (drop off)',
                'Latitude (dropoff)', 'Longitude (dropoff)', 'Timestamp (dropoff)',
                'price per km, Eur', 'waiting time price per h, EUR'
            ]

            required_cargo_columns = [
                'Origin', 'Origin_Latitude', 'Origin_Longitude',
                'Available_From', 'Available_To', 'Delivery_Location',
                'Delivery_Latitude', 'Delivery_Longitude', 'Cargo_Type'
            ]

            if not all(col in trucks_df.columns for col in required_truck_columns):
                st.error(f"Missing required columns in trucks file: {required_truck_columns}")
                return

            if not all(col in cargo_df.columns for col in required_cargo_columns):
                st.error(f"Missing required columns in cargo file: {required_cargo_columns}")
                return

            # Display data preview in expander
            with st.expander("📊 Preview Input Data"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Trucks Data")
                    st.dataframe(trucks_df)
                    if show_debug:
                        st.write("Unique truck types:", trucks_df['truck type'].unique())
                with col2:
                    st.subheader("Cargo Data")
                    st.dataframe(cargo_df)
                    if show_debug:
                        st.write("Unique cargo types:", cargo_df['Cargo_Type'].unique())

            # Show warning if unequal numbers
            if len(trucks_df) != len(cargo_df):
                st.warning(f"⚠️ Unequal numbers of trucks ({len(trucks_df)}) and cargo ({len(cargo_df)}). "
                           f"Some will remain unassigned.")

            try:
                # Initialize calculator with custom speed if provided
                calculator = TimeCostCalculator(standard_speed_kmh=standard_speed)

                # Calculate optimized assignments
                assignments, time_info, rejection_info = optimize_assignments(
                    trucks_df,
                    cargo_df,
                    max_distance_km=250,  # Add default restrictions
                    max_waiting_hours=24
                )

                if assignments:
                    display_results(trucks_df, cargo_df, assignments, time_info, rejection_info, show_debug)
                else:
                    st.error("❌ No valid assignments could be made.")

                    # Display rejection reasons
                    if rejection_info:
                        st.subheader("Assignment Rejection Reasons:")
                        rejection_data = []
                        for (truck_idx, cargo_idx), info in rejection_info.items():
                            rejection_data.append({
                                "Truck ID": info['truck_id'],
                                "Distance (km)": f"{info['distance']:.2f}",
                                "Waiting Hours": f"{info['waiting_hours']:.2f}",
                                "Reason": info['reason']
                            })

                        st.dataframe(pd.DataFrame(rejection_data))

                    st.info("Common rejection reasons:")
                    st.markdown("""
                    - Distance exceeds maximum allowed (250 km)
                    - Waiting time exceeds maximum allowed (24 h)
                    - No matching truck and cargo types
                    - No valid time windows for pickup
                    """)

                    if show_debug:
                        st.write("Debug information:")
                        st.json(time_info)
                        st.json(rejection_info)

            except Exception as e:
                st.error(f"Error during optimization: {str(e)}")
                if show_debug:
                    st.exception(e)
                st.info("Please check your input data and try again.")

        except Exception as e:
            st.error(f"Error loading files: {str(e)}")
            st.info("Please make sure your CSV files have the correct format.")
            if show_debug:
                st.exception(e)
    else:
        show_welcome_message()


def display_results(trucks_df, cargo_df, assignments, time_info, rejection_info, show_debug):
    """Display optimization results with detailed information"""

    # Calculate metrics using the updated function
    metrics = calculate_total_metrics(assignments, time_info, rejection_info)

    # Display main metrics
    st.header("📊 Optimization Results")

    # Show summary metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Cost", f"€{metrics['total_cost']:.2f}")
        st.metric("Distance Cost", f"€{metrics['total_distance_cost']:.2f}")
        st.metric("Waiting Cost", f"€{metrics['total_waiting_cost']:.2f}")
    with col2:
        st.metric("Total Distance", f"{metrics['total_distance']:.2f} km")
        st.metric("Average Distance", f"{metrics['average_distance']:.2f} km")
        st.metric("Total Waiting", f"{metrics['total_waiting_hours']:.2f} h")
    with col3:
        st.metric("Successful Assignments", metrics['assignments_count'])
        st.metric("Assignment Rate", f"{metrics['assignment_rate'] * 100:.1f}%")
        st.metric("Total Rejected", metrics['rejection_stats']['total_rejected'])

    # Create detailed assignments table
    st.subheader("📋 Detailed Assignments")

    assignments_data = []
    for truck_idx, cargo_idx in assignments:
        truck = trucks_df.iloc[truck_idx]
        cargo = cargo_df.iloc[cargo_idx]
        info = time_info[(truck_idx, cargo_idx)]

        assignments_data.append({
            "Truck ID": truck['truck_id'],
            "Truck Type": truck['truck type'],
            "Drop-off Location": truck['Address (drop off)'],
            "Drop-off Time": format_time(truck['Timestamp (dropoff)']),
            "Cargo Type": cargo['Cargo_Type'],
            "Cargo Origin": cargo['Origin'],
            "Cargo Destination": cargo['Delivery_Location'],
            "Available From": format_time(cargo['Available_From']),
            "Available To": format_time(cargo['Available_To']),
            "Pickup Time": format_time(info['pickup_time']),
            "Distance (km)": f"{info['distance']:.2f}",
            "Distance Cost (€)": f"{info['distance_cost']:.2f}",
            "Waiting (h)": f"{info['waiting_hours']:.2f}",
            "Waiting Cost (€)": f"{info['waiting_cost']:.2f}",
            "Total Cost (€)": f"{info['total_cost']:.2f}"
        })

    assignments_df = pd.DataFrame(assignments_data)
    st.dataframe(assignments_df)

    # Add export button for assignments
    st.download_button(
        label="📥 Download Assignments CSV",
        data=assignments_df.to_csv(index=False).encode('utf-8'),
        file_name="assignments.csv",
        mime="text/csv"
    )

    # Display map
    st.header("🗺️ Map Visualization")
    map_obj = create_map(trucks_df, cargo_df, assignments, time_info)
    folium_static(map_obj)

    # Display rejection statistics if any
    if rejection_info:
        st.header("📊 Rejection Statistics")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Rejection Reasons")
            for reason, count in metrics['rejection_stats']['by_reason'].items():
                st.write(f"- {reason}: {count}")

        with col2:
            st.subheader("Rejection Metrics")
            st.write(f"- Rejected by Distance: {metrics['rejection_stats']['rejected_by_distance']}")
            st.write(f"- Rejected by Waiting Time: {metrics['rejection_stats']['rejected_by_waiting_time']}")
            st.write(f"- Rejected by Time Window: {metrics['rejection_stats']['rejected_by_time_window']}")
            if metrics['rejection_stats']['average_rejected_distance'] > 0:
                st.write(
                    f"- Average Rejected Distance: {metrics['rejection_stats']['average_rejected_distance']:.2f} km")
            if metrics['rejection_stats']['average_rejected_waiting_time'] > 0:
                st.write(
                    f"- Average Rejected Waiting Time: {metrics['rejection_stats']['average_rejected_waiting_time']:.2f} h")

    # Display unassigned vehicles and cargo
    assigned_trucks = set(t for t, _ in assignments)
    assigned_cargo = set(c for _, c in assignments)

    if len(assigned_trucks) < len(trucks_df) or len(assigned_cargo) < len(cargo_df):
        st.header("⚠️ Unassigned Items")
        col1, col2 = st.columns(2)

        with col1:
            unassigned_trucks = trucks_df[~trucks_df.index.isin(assigned_trucks)]
            if not unassigned_trucks.empty:
                st.subheader("Unassigned Trucks")
                st.dataframe(unassigned_trucks)

        with col2:
            unassigned_cargo = cargo_df[~cargo_df.index.isin(assigned_cargo)]
            if not unassigned_cargo.empty:
                st.subheader("Unassigned Cargo")
                st.dataframe(unassigned_cargo)

    if show_debug:
        st.header("🔍 Debug Information")
        with st.expander("Show Details"):
            st.write("Time Info:", time_info)
            st.write("Assignments:", assignments)
            st.write("Rejection Info:", rejection_info)
            st.write("Metrics:", metrics)

if __name__ == "__main__":
    main()