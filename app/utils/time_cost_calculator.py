from datetime import datetime, timedelta
from geopy.distance import geodesic

class TimeCostCalculator:
    def __init__(self, standard_speed_kmh=73):
        self.standard_speed_kmh = standard_speed_kmh

    def calculate_travel_time(self, distance_km):
        """Calculate travel time in hours based on distance"""
        return distance_km / self.standard_speed_kmh

    def calculate_pickup_time(self, dropoff_time, distance_km):
        """Calculate pickup time based on dropoff time and distance"""
        travel_time = self.calculate_travel_time(distance_km)
        if isinstance(dropoff_time, str):
            dropoff_time = datetime.strptime(dropoff_time, '%Y-%m-%d %H:%M:%S')
        return dropoff_time - timedelta(hours=travel_time)

    def calculate_waiting_time(self, pickup_time, cargo_available_from):
        """Calculate waiting time in hours if truck arrives early"""
        if isinstance(cargo_available_from, str):
            cargo_available_from = datetime.strptime(cargo_available_from, '%Y-%m-%d %H:%M:%S')
        if pickup_time < cargo_available_from:
            wait_time = cargo_available_from - pickup_time
            return wait_time.total_seconds() / 3600  # Convert to hours
        return 0

    def calculate_total_cost(self, distance_km, waiting_hours, price_per_km, waiting_price_per_hour):
        """Calculate total cost including distance and waiting time"""
        distance_cost = distance_km * price_per_km
        waiting_cost = waiting_hours * waiting_price_per_hour
        return distance_cost + waiting_cost