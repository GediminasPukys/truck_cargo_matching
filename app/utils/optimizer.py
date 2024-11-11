# optimizer.py
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from geopy.distance import geodesic
from datetime import datetime, timedelta


class TimeCostCalculator:
    def __init__(self, standard_speed_kmh=73):
        self.standard_speed_kmh = standard_speed_kmh

    def calculate_travel_time(self, distance_km):
        """Calculate travel time in hours based on distance"""
        return distance_km / self.standard_speed_kmh

    def calculate_pickup_time(self, dropoff_time, distance_km):
        """
        Calculate pickup time based on dropoff time and distance.
        Pickup must happen before dropoff, considering travel time.
        """
        if isinstance(dropoff_time, str):
            dropoff_time = pd.to_datetime(dropoff_time)

        # Calculate travel duration
        travel_time = self.calculate_travel_time(distance_km)
        travel_duration = pd.Timedelta(hours=travel_time)

        # Pickup time must be before dropoff by the travel duration
        pickup_time = dropoff_time - travel_duration
        return pickup_time

    def validate_time_window(self, pickup_time, cargo_available_from, cargo_available_to):
        """
        Validate if pickup time falls within the cargo's available window
        Returns: (is_valid, waiting_hours)
        """
        cargo_available_from = pd.to_datetime(cargo_available_from)
        cargo_available_to = pd.to_datetime(cargo_available_to)

        # Check if pickup is within the available window
        if pickup_time > cargo_available_to:
            return False, 0

        # Calculate waiting time if truck arrives early
        waiting_hours = 0
        if pickup_time < cargo_available_from:
            wait_time = cargo_available_from - pickup_time
            waiting_hours = wait_time.total_seconds() / 3600
            # Use actual pickup time as cargo_available_from
            pickup_time = cargo_available_from

        return True, waiting_hours


def calculate_cost_matrix(trucks_df, cargo_df):
    """Calculate cost matrix between all trucks and cargo"""
    calculator = TimeCostCalculator()
    num_trucks = len(trucks_df)
    num_cargo = len(cargo_df)
    cost_matrix = np.full((num_trucks, num_cargo), np.inf)
    time_info = {}  # Store pickup and waiting times for valid assignments

    for i, truck in trucks_df.iterrows():
        for j, cargo in cargo_df.iterrows():
            # Type matching check (case-insensitive)
            if truck['truck type'].lower() == cargo['Cargo_Type'].lower():
                # Calculate distance
                truck_loc = (truck['Latitude (dropoff)'], truck['Longitude (dropoff)'])
                cargo_loc = (cargo['Delivery_Latitude'], cargo['Delivery_Longitude'])
                distance = geodesic(truck_loc, cargo_loc).kilometers

                # Calculate earliest possible pickup time based on dropoff commitment
                pickup_time = calculator.calculate_pickup_time(
                    truck['Timestamp (dropoff)'],
                    distance
                )

                # Validate pickup time against cargo availability window
                is_valid, waiting_hours = calculator.validate_time_window(
                    pickup_time,
                    cargo['Available_From'],
                    cargo['Available_To']
                )

                if is_valid:
                    # Calculate costs
                    distance_cost = distance * float(truck['price per km, Eur'])
                    waiting_cost = waiting_hours * float(truck['waiting time price per h, EUR'])
                    total_cost = distance_cost + waiting_cost

                    # Store valid assignment information
                    cost_matrix[i, j] = total_cost
                    time_info[(i, j)] = {
                        'pickup_time': pickup_time,
                        'waiting_hours': waiting_hours,
                        'distance_km': distance,
                        'distance_cost': distance_cost,
                        'waiting_cost': waiting_cost,
                        'total_cost': total_cost,
                        'actual_pickup': pickup_time + pd.Timedelta(
                            hours=waiting_hours) if waiting_hours > 0 else pickup_time,
                        'dropoff_time': pd.to_datetime(truck['Timestamp (dropoff)']),
                        'travel_time_hours': calculator.calculate_travel_time(distance)
                    }

    return cost_matrix, time_info


def optimize_assignments(trucks_df, cargo_df):
    """
    Optimize assignments between trucks and cargo based on total cost
    Returns list of (truck_idx, cargo_idx) tuples and time information dictionary
    """
    # Calculate cost matrix and time information
    cost_matrix, time_info = calculate_cost_matrix(trucks_df, cargo_df)

    # Check if any valid assignments exist
    if np.all(np.isinf(cost_matrix)):
        return [], {}

    # Solve the assignment problem
    row_ind, col_ind = linear_sum_assignment(np.nan_to_num(cost_matrix, nan=1e10, posinf=1e10))

    # Filter out invalid assignments (infinite cost)
    valid_assignments = [
        (r, c) for r, c in zip(row_ind, col_ind)
        if not np.isinf(cost_matrix[r, c]) and (r, c) in time_info
    ]

    # If no valid assignments found after filtering
    if not valid_assignments:
        return [], {}

    return valid_assignments, time_info


def calculate_total_metrics(assignments, time_info):
    """Calculate total distance, cost, and waiting time for all assignments"""
    if not assignments:
        return {
            'total_distance': 0,
            'total_distance_cost': 0,
            'total_waiting_hours': 0,
            'total_waiting_cost': 0,
            'total_cost': 0,
            'average_travel_time': 0
        }

    total_distance = sum(time_info[a]['distance_km'] for a in assignments)
    total_distance_cost = sum(time_info[a]['distance_cost'] for a in assignments)
    total_waiting_hours = sum(time_info[a]['waiting_hours'] for a in assignments)
    total_waiting_cost = sum(time_info[a]['waiting_cost'] for a in assignments)
    total_cost = sum(time_info[a]['total_cost'] for a in assignments)
    avg_travel_time = sum(time_info[a]['travel_time_hours'] for a in assignments) / len(assignments)

    return {
        'total_distance': total_distance,
        'total_distance_cost': total_distance_cost,
        'total_waiting_hours': total_waiting_hours,
        'total_waiting_cost': total_waiting_cost,
        'total_cost': total_cost,
        'average_travel_time': avg_travel_time
    }