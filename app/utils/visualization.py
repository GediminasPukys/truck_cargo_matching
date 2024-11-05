# utils/visualization.py
import folium
import pandas as pd
from datetime import datetime
from folium import plugins


def create_map(trucks_df, cargo_df, assignments, time_info):
    """
    Create a Folium map with detailed time and cost information
    """
    # Calculate the center of all points
    all_lats = pd.concat([
        trucks_df['Latitude (dropoff)'],
        cargo_df['Delivery_Latitude']
    ])
    all_lons = pd.concat([
        trucks_df['Longitude (dropoff)'],
        cargo_df['Delivery_Longitude']
    ])
    center_lat = all_lats.mean()
    center_lon = all_lons.mean()

    # Create the base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='cartodbpositron'
    )

    # Add fullscreen option
    plugins.Fullscreen().add_to(m)

    # Track assigned trucks and cargo
    assigned_trucks = set()
    assigned_cargo = set()

    # Add lines and markers for assigned pairs
    for truck_idx, cargo_idx in assignments:
        assigned_trucks.add(truck_idx)
        assigned_cargo.add(cargo_idx)

        truck = trucks_df.iloc[truck_idx]
        cargo = cargo_df.iloc[cargo_idx]
        assignment_info = time_info[(truck_idx, cargo_idx)]

        # Format truck popup
        truck_popup = f"""
            <div style='font-family: Arial; min-width: 200px'>
                <h4 style='margin-bottom: 10px'>Truck Information</h4>
                <b>ID:</b> {truck['truck_id']}<br>
                <b>Type:</b> {truck['truck type']}<br>
                <b>Location:</b> {truck['Address (drop off)']}<br>
                <b>Drop-off Time:</b> {truck['Timestamp (dropoff)']}<br>
                <b>Price per km:</b> €{truck['price per km, Eur']}<br>
                <b>Waiting price:</b> €{truck['waiting time price per h, EUR']}/h<br>
                <hr>
                <h4 style='margin-bottom: 10px'>Assignment Details</h4>
                <b>Pickup Time:</b> {assignment_info['pickup_time'].strftime('%Y-%m-%d %H:%M:%S')}<br>
                <b>Distance Cost:</b> €{assignment_info['distance_cost']:.2f}<br>
                <b>Waiting Time:</b> {assignment_info['waiting_hours']:.2f} hours<br>
                <b>Waiting Cost:</b> €{assignment_info['waiting_cost']:.2f}<br>
                <b>Total Cost:</b> €{assignment_info['total_cost']:.2f}
            </div>
        """

        # Add truck marker
        folium.Marker(
            location=[truck['Latitude (dropoff)'], truck['Longitude (dropoff)']],
            popup=folium.Popup(truck_popup, max_width=300),
            icon=folium.Icon(
                color='green',
                icon='truck',
                prefix='fa'
            ),
            tooltip=f"Truck {truck['truck_id']} - Click for details"
        ).add_to(m)

        # Format cargo popup
        cargo_popup = f"""
            <div style='font-family: Arial; min-width: 200px'>
                <h4 style='margin-bottom: 10px'>Cargo Information</h4>
                <b>Type:</b> {cargo['Cargo_Type']}<br>
                <b>From:</b> {cargo['Origin']}<br>
                <b>To:</b> {cargo['Delivery_Location']}<br>
                <b>Available From:</b> {cargo['Available_From']}<br>
                <b>Available To:</b> {cargo['Available_To']}<br>
                <hr>
                <h4 style='margin-bottom: 10px'>Pickup Details</h4>
                <b>Assigned Truck:</b> {truck['truck_id']}<br>
                <b>Pickup Time:</b> {assignment_info['pickup_time'].strftime('%Y-%m-%d %H:%M:%S')}<br>
                <b>Waiting Time:</b> {assignment_info['waiting_hours']:.2f} hours
            </div>
        """

        # Add cargo marker
        folium.Marker(
            location=[cargo['Delivery_Latitude'], cargo['Delivery_Longitude']],
            popup=folium.Popup(cargo_popup, max_width=300),
            icon=folium.Icon(
                color='green',
                icon='box',
                prefix='fa'
            ),
            tooltip=f"Cargo {cargo['Cargo_Type']} - Click for details"
        ).add_to(m)

        # Create connection line with detailed information
        line_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [truck['Longitude (dropoff)'], truck['Latitude (dropoff)']],
                    [cargo['Delivery_Longitude'], cargo['Delivery_Latitude']]
                ]
            },
            "properties": {
                "distance": f"{assignment_info['distance']:.2f} km",
                "pickup_time": assignment_info['pickup_time'].strftime('%Y-%m-%d %H:%M:%S'),
                "waiting_time": f"{assignment_info['waiting_hours']:.2f} h",
                "total_cost": f"€{assignment_info['total_cost']:.2f}"
            }
        }

        # Add line with hover effect
        folium.GeoJson(
            line_feature,
            style_function=lambda x: {
                'color': 'green',
                'weight': 2,
                'opacity': 0.8
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['distance', 'pickup_time', 'waiting_time', 'total_cost'],
                aliases=['Distance:', 'Pickup Time:', 'Waiting Time:', 'Total Cost:'],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
            )
        ).add_to(m)

    # Add unassigned trucks
    for idx, truck in trucks_df.iterrows():
        if idx not in assigned_trucks:
            unassigned_truck_popup = f"""
                <div style='font-family: Arial; min-width: 200px'>
                    <h4 style='margin-bottom: 10px'>Unassigned Truck</h4>
                    <b>ID:</b> {truck['truck_id']}<br>
                    <b>Type:</b> {truck['truck type']}<br>
                    <b>Location:</b> {truck['Address (drop off)']}<br>
                    <b>Drop-off Time:</b> {truck['Timestamp (dropoff)']}<br>
                    <b>Price per km:</b> €{truck['price per km, Eur']}<br>
                    <b>Waiting price:</b> €{truck['waiting time price per h, EUR']}/h
                </div>
            """

            folium.Marker(
                location=[truck['Latitude (dropoff)'], truck['Longitude (dropoff)']],
                popup=folium.Popup(unassigned_truck_popup, max_width=300),
                icon=folium.Icon(
                    color='red',
                    icon='truck',
                    prefix='fa'
                ),
                tooltip=f"Unassigned Truck {truck['truck_id']} - Click for details"
            ).add_to(m)

    # Add unassigned cargo
    for idx, cargo in cargo_df.iterrows():
        if idx not in assigned_cargo:
            unassigned_cargo_popup = f"""
                <div style='font-family: Arial; min-width: 200px'>
                    <h4 style='margin-bottom: 10px'>Unassigned Cargo</h4>
                    <b>Type:</b> {cargo['Cargo_Type']}<br>
                    <b>From:</b> {cargo['Origin']}<br>
                    <b>To:</b> {cargo['Delivery_Location']}<br>
                    <b>Available From:</b> {cargo['Available_From']}<br>
                    <b>Available To:</b> {cargo['Available_To']}
                </div>
            """

            folium.Marker(
                location=[cargo['Delivery_Latitude'], cargo['Delivery_Longitude']],
                popup=folium.Popup(unassigned_cargo_popup, max_width=300),
                icon=folium.Icon(
                    color='red',
                    icon='box',
                    prefix='fa'
                ),
                tooltip=f"Unassigned Cargo - Click for details"
            ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m