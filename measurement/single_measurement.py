"""
Perform a single measurement. Also notes the kind of measurement performed.

Usage:
    python single_measurement.py --measurement_type "full_swing"/"interferometry"
"""
import argparse
import time as t
import datetime as dt
import dwfpy as dwf
import numpy as np
import json
from pathlib import Path
# from trap_tester.utils import R_SENSE, SENSE_MAG

"""-----------------------------------------------------------------------"""

# Measurement settings
f_sample = 1e3  # Sample rate in Hz
measurement_duration = 8.0  # Duration in seconds
buffer_size = int(measurement_duration * f_sample)  # Calculate buffer_size from duration

# Scope channel settings
CHANNEL_RANGE = 0.5  # Volts (±5V range)

# Results directory
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Perform a single measurement.")
    parser.add_argument(
        "--measurement_type",
        required=True,
        help='Measurement type (full_swing or interferometry).',
        choices=["full_swing", "interferometry"],
    )
    return parser.parse_args()

def get_date_directory() -> Path:
    """Create and return the hierarchical date-based directory: results/YYYY/MM/DD"""
    now = dt.datetime.now()
    date_dir = RESULTS_DIR / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir

def main() -> None:
    args = parse_args()
    measurement_type = args.measurement_type
    data_prefix = "full_swing" if measurement_type == "full_swing" else "v_meas"

    with dwf.Device() as device:
        # Initialize scope
        scope = device.analog_input
        scope[0].setup(range=CHANNEL_RANGE)
        
        # Get timestamp when measurement starts
        measurement_timestamp = t.strftime("%Y%m%d-%H%M%S")
        
        print(f"Starting measurement at {t.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sample rate: {f_sample} Hz, Duration: {measurement_duration} s, Buffer size: {buffer_size}")
        
        # Perform single measurement
        scope.single(sample_rate=f_sample, buffer_size=buffer_size, configure=True, start=True)
        
        # Get measurement data
        v_meas = scope[0].get_data()  # Voltage in V
        
        # Get trigger time information from device
        # Returns tuple: (sec_utc, tick, ticks_per_second)
        #   - sec_utc: System time in seconds (UTC, Unix epoch) when trigger occurred
        #   - tick: Sample tick/index in buffer where trigger occurred
        #   - ticks_per_second: Sample rate in ticks/second (should match f_sample)
        trigger_time_info = scope.time
        sec_utc, trigger_tick, ticks_per_second = trigger_time_info
        
        # Create time array for each measurement point (relative to trigger, in seconds)
        # This is the standard approach: time = sample_index / sample_rate
        # Samples are acquired at regular intervals, so time is calculated from sample rate
        time_array = np.arange(len(v_meas)) / f_sample
        
        # Optional: Calculate absolute timestamps (UTC seconds) for each sample
        # This combines the trigger system time with relative sample times
        # absolute_timestamps = sec_utc + (trigger_tick + np.arange(len(v_meas))) / ticks_per_second
        
        print(f"Measurement completed. Captured {len(v_meas)} samples.")
        print(f"Trigger time info:")
        print(f"  - System time (UTC): {sec_utc} seconds since Unix epoch")
        print(f"  - Trigger tick: {trigger_tick} (sample index where trigger occurred)")
        print(f"  - Ticks per second: {ticks_per_second} (device sample rate)")
        
        # Save v_meas data with timestamp in hierarchical date-based directory
        date_dir = get_date_directory()
        filename = date_dir / f"{data_prefix}_{measurement_timestamp}.json"
        
        # Prepare data dictionary with metadata and measurements
        data_to_save = {
            "timestamp": measurement_timestamp,
            "measurement_time": t.strftime("%Y-%m-%d %H:%M:%S"),
            "sec_utc": int(sec_utc),  # System time in seconds (UTC, Unix epoch)
            "sample_rate_hz": float(f_sample),
            "measurement_duration_s": float(measurement_duration),
            "buffer_size": int(buffer_size),
            "channel_range_v": float(CHANNEL_RANGE),
            "time_s": time_array.tolist(),  # Time array in seconds (relative to trigger)
            "voltage_data_v": v_meas.tolist()  # Convert numpy array to list for JSON
        }
        
        # Save to JSON file
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        
        print(f"Data saved to: {filename}")

if __name__ == "__main__":
    main()