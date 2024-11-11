# optimizer.py
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from geopy.distance import geodesic
from datetime import datetime, timedelta

class TimeCostCalculator:
    def __init__(self, standard_speed_kmh=73, max_distance_km=250, max_waiting_hours=24):
        self.standard_speed_kmh = standard_speed_kmh
        self.max_distance_km = max_distance_km
        self.max_waiting_hours = max_waiting_hours

    def calculate_travel_time(self, distance):
        """Calculate travel time in hours based on distance"""
        return distance / self.standard_speed_kmh

    def calculate_pickup_possibilities(self, truck_available_from, distance, cargo_available_from, cargo_available_to):
        """
        Calculate possible pickup time based on when truck becomes available and cargo time window.

        Args:
            truck_available_from: When truck becomes available (previous dropoff time)
            distance: Distance to cargo location
            cargo_available_from: Start of cargo pickup window
            cargo_available_to: End of cargo pickup window

        Returns:
            (is_valid, pickup_time, waiting_hours, rejection_reason)
        """
        # Check distance restriction first
        if distance > self.max_distance_km:
            return False, None, 0, f"Distance ({distance:.1f} km) exceeds maximum allowed ({self.max_distance_km} km)"

        # Convert all times to pandas datetime
        truck_available = pd.to_datetime(truck_available_from)
        cargo_from = pd.to_datetime(cargo_available_from)
        cargo_to = pd.to_datetime(cargo_available_to)

        # Calculate how long it takes to reach cargo location
        travel_to_cargo = pd.Timedelta(hours=self.calculate_travel_time(distance))

        # Earliest possible time truck can reach cargo location
        earliest_possible_arrival = truck_available + travel_to_cargo

        # If truck can't reach cargo before the pickup window ends
        if earliest_possible_arrival > cargo_to:
            return False, None, 0, "Truck arrives after cargo available window ends"

        # If truck arrives before cargo is available, it must wait
        if earliest_possible_arrival < cargo_from:
            waiting_hours = (cargo_from - earliest_possible_arrival).total_seconds() / 3600
            if waiting_hours > self.max_waiting_hours:
                return False, None, 0, f"Waiting time ({waiting_hours:.1f} h) exceeds maximum allowed ({self.max_waiting_hours} h)"
            pickup_time = cargo_from
        else:
            waiting_hours = 0
            pickup_time = earliest_possible_arrival

        return True, pickup_time, waiting_hours, "Valid assignment"

def calculate_cost_matrix(trucks_df, cargo_df, max_distance_km=250, max_waiting_hours=24):
    """Calculate cost matrix between all trucks and cargo"""
    calculator = TimeCostCalculator(
        max_distance_km=max_distance_km,
        max_waiting_hours=max_waiting_hours
    )
    num_trucks = len(trucks_df)
    num_cargo = len(cargo_df)
    cost_matrix = np.full((num_trucks, num_cargo), np.inf)
    time_info = {}
    rejection_info = {}

    for i, truck in trucks_df.iterrows():
        for j, cargo in cargo_df.iterrows():
            # Type matching check (case-insensitive)
            if truck['truck type'].lower() == cargo['Cargo_Type'].lower():
                # Calculate distance
                truck_loc = (truck['Latitude (dropoff)'], truck['Longitude (dropoff)'])
                cargo_loc = (cargo['Delivery_Latitude'], cargo['Delivery_Longitude'])
                distance = geodesic(truck_loc, cargo_loc).kilometers

                # Calculate pickup possibilities
                is_valid, pickup_time, waiting_hours, rejection_reason = calculator.calculate_pickup_possibilities(
                    truck['Timestamp (dropoff)'],  # This is when truck becomes available
                    distance,
                    cargo['Available_From'],
                    cargo['Available_To']
                )

                if is_valid:
                    # Calculate travel time
                    travel_time = calculator.calculate_travel_time(distance)

                    # Calculate costs
                    distance_cost = distance * float(truck['price per km, Eur'])
                    waiting_cost = waiting_hours * float(truck['waiting time price per h, EUR'])
                    total_cost = distance_cost + waiting_cost

                    # Store valid assignment information
                    cost_matrix[i, j] = total_cost
                    time_info[(i, j)] = {
                        'truck_available_from': pd.to_datetime(truck['Timestamp (dropoff)']),
                        'cargo_available_from': pd.to_datetime(cargo['Available_From']),
                        'cargo_available_to': pd.to_datetime(cargo['Available_To']),
                        'travel_to_cargo_hours': travel_time,
                        'waiting_hours': waiting_hours,
                        'pickup_time': pickup_time,
                        'distance': distance,
                        'distance_cost': distance_cost,
                        'waiting_cost': waiting_cost,
                        'total_cost': total_cost,
                        'timeline': {
                            'truck_available': pd.to_datetime(truck['Timestamp (dropoff)']),
                            'travel_to_cargo_starts': pd.to_datetime(truck['Timestamp (dropoff)']),
                            'arrival_at_cargo': pd.to_datetime(truck['Timestamp (dropoff)']) + pd.Timedelta(hours=travel_time),
                            'actual_pickup': pickup_time
                        }
                    }
                else:
                    rejection_info[(i, j)] = {
                        'truck_id': truck['truck_id'],
                        'cargo_id': j,
                        'distance': distance,
                        'waiting_hours': waiting_hours,
                        'reason': rejection_reason
                    }

    return cost_matrix, time_info, rejection_info

def optimize_assignments(trucks_df, cargo_df, max_distance_km=250, max_waiting_hours=24):
    """
    Optimize assignments between trucks and cargo based on total cost
    Returns list of (truck_idx, cargo_idx) tuples, time information dictionary, and rejection information
    """
    cost_matrix, time_info, rejection_info = calculate_cost_matrix(
        trucks_df,
        cargo_df,
        max_distance_km=max_distance_km,
        max_waiting_hours=max_waiting_hours
    )

    # Check if any valid assignments exist
    if np.all(np.isinf(cost_matrix)):
        return [], {}, rejection_info

    # Solve the assignment problem
    row_ind, col_ind = linear_sum_assignment(np.nan_to_num(cost_matrix, nan=1e10, posinf=1e10))

    # Filter out invalid assignments (infinite cost)
    valid_assignments = [
        (r, c) for r, c in zip(row_ind, col_ind)
        if not np.isinf(cost_matrix[r, c]) and (r, c) in time_info
    ]

    if not valid_assignments:
        return [], {}, rejection_info

    return valid_assignments, time_info, rejection_info


def calculate_total_metrics(assignments, time_info, rejection_info=None):
    """
    Calculate total distance, cost, waiting time, and rejection statistics for all assignments

    Args:
        assignments: List of (truck_idx, cargo_idx) tuples of valid assignments
        time_info: Dictionary containing detailed timing and cost information
        rejection_info: Dictionary containing information about rejected assignments

    Returns:
        Dictionary containing aggregated metrics
    """
    # Initialize metrics for no assignments case
    metrics = {
        'total_distance': 0,
        'total_distance_cost': 0,
        'total_waiting_hours': 0,
        'total_waiting_cost': 0,
        'total_cost': 0,
        'average_distance': 0,
        'average_waiting_time': 0,
        'average_cost': 0,
        'assignments_count': 0,
        'rejection_stats': {
            'total_rejected': 0,
            'by_reason': {},
            'rejected_by_distance': 0,
            'rejected_by_waiting_time': 0,
            'rejected_by_time_window': 0,
            'average_rejected_distance': 0,
            'average_rejected_waiting_time': 0
        }
    }

    # If no assignments, but we have rejection info, calculate rejection statistics
    if not assignments and rejection_info:
        metrics['rejection_stats']['total_rejected'] = len(rejection_info)

        # Calculate rejection statistics
        rejected_distances = []
        rejected_waiting_times = []

        for info in rejection_info.values():
            reason = info['reason']
            metrics['rejection_stats']['by_reason'][reason] = \
                metrics['rejection_stats']['by_reason'].get(reason, 0) + 1

            # Track specific rejection types
            if 'distance' in reason.lower():
                metrics['rejection_stats']['rejected_by_distance'] += 1
                rejected_distances.append(info['distance'])
            elif 'waiting time' in reason.lower():
                metrics['rejection_stats']['rejected_by_waiting_time'] += 1
                rejected_waiting_times.append(info['waiting_hours'])
            elif 'window' in reason.lower():
                metrics['rejection_stats']['rejected_by_time_window'] += 1

        # Calculate averages for rejected assignments
        if rejected_distances:
            metrics['rejection_stats']['average_rejected_distance'] = \
                sum(rejected_distances) / len(rejected_distances)
        if rejected_waiting_times:
            metrics['rejection_stats']['average_rejected_waiting_time'] = \
                sum(rejected_waiting_times) / len(rejected_waiting_times)

        return metrics

    # Calculate metrics for valid assignments
    if assignments:
        metrics['assignments_count'] = len(assignments)

        # Calculate totals
        total_distance = sum(time_info[a]['distance'] for a in assignments)
        total_distance_cost = sum(time_info[a]['distance_cost'] for a in assignments)
        total_waiting_hours = sum(time_info[a]['waiting_hours'] for a in assignments)
        total_waiting_cost = sum(time_info[a]['waiting_cost'] for a in assignments)
        total_cost = sum(time_info[a]['total_cost'] for a in assignments)

        # Store total metrics
        metrics.update({
            'total_distance': total_distance,
            'total_distance_cost': total_distance_cost,
            'total_waiting_hours': total_waiting_hours,
            'total_waiting_cost': total_waiting_cost,
            'total_cost': total_cost,

            # Calculate averages
            'average_distance': total_distance / len(assignments),
            'average_waiting_time': total_waiting_hours / len(assignments),
            'average_cost': total_cost / len(assignments)
        })

    # Add rejection statistics if available
    if rejection_info:
        metrics['rejection_stats']['total_rejected'] = len(rejection_info)

        # Calculate rejection statistics
        rejected_distances = []
        rejected_waiting_times = []

        for info in rejection_info.values():
            reason = info['reason']
            metrics['rejection_stats']['by_reason'][reason] = \
                metrics['rejection_stats']['by_reason'].get(reason, 0) + 1

            # Track specific rejection types
            if 'distance' in reason.lower():
                metrics['rejection_stats']['rejected_by_distance'] += 1
                rejected_distances.append(info['distance'])
            elif 'waiting time' in reason.lower():
                metrics['rejection_stats']['rejected_by_waiting_time'] += 1
                rejected_waiting_times.append(info['waiting_hours'])
            elif 'window' in reason.lower():
                metrics['rejection_stats']['rejected_by_time_window'] += 1

        # Calculate averages for rejected assignments
        if rejected_distances:
            metrics['rejection_stats']['average_rejected_distance'] = \
                sum(rejected_distances) / len(rejected_distances)
        if rejected_waiting_times:
            metrics['rejection_stats']['average_rejected_waiting_time'] = \
                sum(rejected_waiting_times) / len(rejected_waiting_times)

        # Add assignment rate
        total_attempts = len(assignments) + len(rejection_info)
        metrics['assignment_rate'] = len(assignments) / total_attempts if total_attempts > 0 else 0

    return metrics