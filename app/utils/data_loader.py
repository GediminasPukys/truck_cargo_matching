import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np


class DataValidator:
    """Class to handle data validation rules and checks"""

    @staticmethod
    def validate_coordinates(lat, lon):
        """Validate latitude and longitude values"""
        try:
            lat = float(lat)
            lon = float(lon)
            return -90 <= lat <= 90 and -180 <= lon <= 180
        except:
            return False

    @staticmethod
    def validate_timestamp(timestamp):
        """Validate timestamp format"""
        try:
            if isinstance(timestamp, str):
                pd.to_datetime(timestamp)
            return True
        except:
            return False

    @staticmethod
    def validate_numeric(value):
        """Validate numeric values"""
        try:
            float_val = float(str(value).replace(',', '.'))
            return float_val > 0
        except:
            return False


class DataLoader:
    """Class to handle data loading and validation"""

    def __init__(self):
        self.validator = DataValidator()

    def load_trucks_data(self, file):
        """
        Load and validate trucks data from CSV file

        Required columns:
        - truck_id: unique identifier
        - truck type: type of truck
        - Address (drop off): drop-off location name
        - Latitude (dropoff): drop-off latitude
        - Longitude (dropoff): drop-off longitude
        - Timestamp (dropoff): drop-off time
        - avg moving speed, km/h: average speed
        - price per km, Eur: price per kilometer
        - waiting time price per h, EUR: waiting time price
        """
        try:
            # Read CSV file
            df = pd.read_csv(file)

            # Check required columns
            required_columns = [
                'truck_id',
                'truck type',
                'Address (drop off)',
                'Latitude (dropoff)',
                'Longitude (dropoff)',
                'Timestamp (dropoff)',
                'avg moving speed, km/h',
                'price per km, Eur',
                'waiting time price per h, EUR'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns in trucks file: {', '.join(missing_columns)}")
                return None

            # Validate data
            validation_errors = []

            # Check for duplicate truck IDs
            if df['truck_id'].duplicated().any():
                validation_errors.append("Duplicate truck IDs found")

            # Validate coordinates
            invalid_coords = df.apply(
                lambda row: not self.validator.validate_coordinates(
                    row['Latitude (dropoff)'],
                    row['Longitude (dropoff)']
                ),
                axis=1
            )
            if invalid_coords.any():
                validation_errors.append(
                    f"Invalid coordinates found in rows: {list(df[invalid_coords].index)}"
                )

            # Validate timestamp
            invalid_timestamps = df.apply(
                lambda row: not self.validator.validate_timestamp(row['Timestamp (dropoff)']),
                axis=1
            )
            if invalid_timestamps.any():
                validation_errors.append(
                    f"Invalid timestamps found in rows: {list(df[invalid_timestamps].index)}"
                )

            # Validate numeric values
            numeric_columns = [
                'avg moving speed, km/h',
                'price per km, Eur',
                'waiting time price per h, EUR'
            ]

            for col in numeric_columns:
                invalid_numbers = df.apply(
                    lambda row: not self.validator.validate_numeric(row[col]),
                    axis=1
                )
                if invalid_numbers.any():
                    validation_errors.append(
                        f"Invalid {col} values found in rows: {list(df[invalid_numbers].index)}"
                    )

            # Report validation errors
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return None

            # Clean and convert data types
            df['Timestamp (dropoff)'] = pd.to_datetime(df['Timestamp (dropoff)'])
            df['Latitude (dropoff)'] = pd.to_numeric(df['Latitude (dropoff)'])
            df['Longitude (dropoff)'] = pd.to_numeric(df['Longitude (dropoff)'])
            df['avg moving speed, km/h'] = pd.to_numeric(df['avg moving speed, km/h'])
            df['price per km, Eur'] = pd.to_numeric(df['price per km, Eur'].astype(str).str.replace(',', '.'))
            df['waiting time price per h, EUR'] = pd.to_numeric(
                df['waiting time price per h, EUR'].astype(str).str.replace(',', '.'))

            # Add validation success message
            st.success(f"Successfully loaded {len(df)} trucks")

            return df

        except Exception as e:
            st.error(f"Error loading trucks file: {str(e)}")
            return None

    def load_cargo_data(self, file):
        """
        Load and validate cargo data from CSV file

        Required columns:
        - Origin: origin location name
        - Origin_Latitude: origin latitude
        - Origin_Longitude: origin longitude
        - Available_From: availability start time
        - Available_To: availability end time
        - Delivery_Location: delivery location name
        - Delivery_Latitude: delivery latitude
        - Delivery_Longitude: delivery longitude
        - Cargo_Type: type of cargo
        """
        try:
            # Read CSV file
            df = pd.read_csv(file)

            # Check required columns
            required_columns = [
                'Origin',
                'Origin_Latitude',
                'Origin_Longitude',
                'Available_From',
                'Available_To',
                'Delivery_Location',
                'Delivery_Latitude',
                'Delivery_Longitude',
                'Cargo_Type'
            ]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns in cargo file: {', '.join(missing_columns)}")
                return None

            # Validate data
            validation_errors = []

            # Validate origin coordinates
            invalid_origin_coords = df.apply(
                lambda row: not self.validator.validate_coordinates(
                    row['Origin_Latitude'],
                    row['Origin_Longitude']
                ),
                axis=1
            )
            if invalid_origin_coords.any():
                validation_errors.append(
                    f"Invalid origin coordinates found in rows: {list(df[invalid_origin_coords].index)}"
                )

            # Validate delivery coordinates
            invalid_delivery_coords = df.apply(
                lambda row: not self.validator.validate_coordinates(
                    row['Delivery_Latitude'],
                    row['Delivery_Longitude']
                ),
                axis=1
            )
            if invalid_delivery_coords.any():
                validation_errors.append(
                    f"Invalid delivery coordinates found in rows: {list(df[invalid_delivery_coords].index)}"
                )

            # Validate timestamps
            invalid_from_times = df.apply(
                lambda row: not self.validator.validate_timestamp(row['Available_From']),
                axis=1
            )
            if invalid_from_times.any():
                validation_errors.append(
                    f"Invalid Available_From timestamps found in rows: {list(df[invalid_from_times].index)}"
                )

            invalid_to_times = df.apply(
                lambda row: not self.validator.validate_timestamp(row['Available_To']),
                axis=1
            )
            if invalid_to_times.any():
                validation_errors.append(
                    f"Invalid Available_To timestamps found in rows: {list(df[invalid_to_times].index)}"
                )

            # Validate time windows
            df['Available_From'] = pd.to_datetime(df['Available_From'])
            df['Available_To'] = pd.to_datetime(df['Available_To'])
            invalid_windows = df['Available_From'] >= df['Available_To']
            if invalid_windows.any():
                validation_errors.append(
                    f"Invalid time windows (From >= To) found in rows: {list(df[invalid_windows].index)}"
                )

            # Report validation errors
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return None

            # Clean and convert data types
            df['Origin_Latitude'] = pd.to_numeric(df['Origin_Latitude'])
            df['Origin_Longitude'] = pd.to_numeric(df['Origin_Longitude'])
            df['Delivery_Latitude'] = pd.to_numeric(df['Delivery_Latitude'])
            df['Delivery_Longitude'] = pd.to_numeric(df['Delivery_Longitude'])

            # Add validation success message
            st.success(f"Successfully loaded {len(df)} cargo items")

            return df

        except Exception as e:
            st.error(f"Error loading cargo file: {str(e)}")
            return None


def load_data(trucks_file, cargo_file):
    """
    Main function to load both trucks and cargo data
    Returns tuple of (trucks_df, cargo_df) or (None, None) if validation fails
    """
    loader = DataLoader()

    trucks_df = loader.load_trucks_data(trucks_file) if trucks_file is not None else None
    cargo_df = loader.load_cargo_data(cargo_file) if cargo_file is not None else None

    if trucks_df is not None and cargo_df is not None:
        # Additional cross-validation
        truck_types = set(trucks_df['truck type'].str.lower())
        cargo_types = set(cargo_df['Cargo_Type'].str.lower())

        # Check for matching types
        if not truck_types.intersection(cargo_types):
            st.warning("No matching truck and cargo types found!")
            st.write("Truck types:", truck_types)
            st.write("Cargo types:", cargo_types)

        return trucks_df, cargo_df

    return None, None