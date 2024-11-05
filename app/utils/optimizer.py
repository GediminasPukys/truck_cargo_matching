# utils/optimizer.py
import numpy as np
from scipy.optimize import linear_sum_assignment
from geopy.distance import geodesic
from .time_cost_calculator import TimeCostCalculator


def calculate_cost_matrix(trucks_df, cargo_df):
    """Calculate cost matrix between all trucks and cargo"""
    calculator = TimeCostCalculator()
    num_trucks = len(trucks_df)
    num_cargo = len(cargo_df)
    cost_matrix = np.full((num_trucks, num_cargo), np.inf)
    time_info = {}  # Store pickup and waiting times for valid assignments

    for i, truck in trucks_df.iterrows():
        for j, cargo in cargo_df.iterrows():
            # Calculate distance
            truck_loc = (truck['Latitude (dropoff)'], truck['Longitude (dropoff)'])
            cargo_loc = (cargo['Delivery_Latitude'], cargo['Delivery_Longitude'])
            distance = geodesic(truck_loc, cargo_loc).kilometers

            # Calculate pickup time
            pickup_time = calculator.calculate_pickup_time(
                truck['Timestamp (dropoff)'],
                distance
            )

            # Calculate waiting time if truck arrives early
            waiting_hours = calculator.calculate_waiting_time(
                pickup_time,
                cargo['Available_From']
            )

            # Calculate total cost
            total_cost = calculator.calculate_total_cost(
                distance,
                waiting_hours,
                float(truck['price per km, Eur']),
                float(truck['waiting time price per h, EUR'])
            )

            # Store time information if the assignment is valid
            cargo_available_to = datetime.strptime(cargo['Available_To'], '%Y-%m-%d %H:%M:%S')
            if pickup_time <= cargo_available_to:
                cost_matrix[i, j] = total_cost
                time_info[(i, j)] = {
                    'pickup_time': pickup_time,
                    'waiting_hours': waiting_hours,
                    'distance': distance,
                    'distance_cost': distance * float(truck['price per km, Eur']),
                    'waiting_cost': waiting_hours * float(truck['waiting time price per h, EUR']),
                    'total_cost': total_cost
                }

    return cost_matrix, time_info


def optimize_assignments(trucks_df, cargo_df):
    """Optimize assignments based on total cost"""
    cost_matrix, time_info = calculate_cost_matrix(trucks_df, cargo_df)

    # Solve the assignment problem
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # Filter out invalid assignments (infinite cost)
    valid_assignments = [
        (r, c) for r, c in zip(row_ind, col_ind)
        if cost_matrix[r, c] != np.inf
    ]

    return valid_assignments, time_info