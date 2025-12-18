"""
Simple loop: keep taking measurements until a target end time.

Usage:
    python measure_until_time_simple.py --end "2025-12-11 15:30:00"
"""

import argparse
import datetime as dt
import json
import time as t
from pathlib import Path

import dwfpy as dwf
import numpy as np

# Measurement settings (same defaults as demo_scope.py)
F_SAMPLE = 1e3  # Hz
MEAS_DURATION = 8.0  # seconds
BUFFER_SIZE = int(MEAS_DURATION * F_SAMPLE)
CHANNEL_RANGE = 0.5  # Volts (±range)
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
LOG_FILE = Path(__file__).parent / "measurements_log.json"


def load_log() -> dict:
    """Load existing log file or return empty dict if it doesn't exist or is empty."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:

        with open(LOG_FILE, "r") as f:
            return json.load(f)

    return {}


def save_log(log_data: dict) -> None:
    """Save log data to JSON file."""
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)


def get_date_directory() -> Path:
    """Create and return the hierarchical date-based directory: results/YYYY/MM/DD"""
    now = dt.datetime.now()
    date_dir = RESULTS_DIR / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run measurements until the specified end datetime.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using individual arguments:
  python measurement_with_log.py --end "2025-12-11 15:30:00" --measurement_type interferometry --description "Test run"
  
  # Using JSON config file:
  python measurement_with_log.py --config config.json
        """
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file containing arguments (alternative to individual arguments).",
    )
    parser.add_argument(
        "--end",
        help='End datetime (inclusive) in "YYYY-MM-DD HH:MM:SS" (local time).',
    )
    parser.add_argument(
        "--measurement_type",
        help='Type of measurement (full_swing or interferometry).',
        choices=["full_swing", "interferometry"],
    )
    parser.add_argument(
        "--description",
        help='Comment for the measurement.',
    )
    
    args = parser.parse_args()
    
    # If config file is provided, load arguments from it
    if args.config:
        config_path = Path(__file__).parent / args.config
        if not config_path.exists():
            parser.error(f"Config file not found: {args.config}")
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Override with config file values if not provided via command line
        if args.end is None:
            args.end = config.get("end")
        if args.measurement_type is None:
            args.measurement_type = config.get("measurement_type")
        if args.description is None:
            args.description = config.get("description")
    
    # Validate required arguments
    if args.end is None:
        parser.error("--end is required (or provide via --config)")
    if args.measurement_type is None:
        parser.error("--measurement_type is required (or provide via --config)")
    if args.description is None:
        parser.error("--description is required (or provide via --config)")
    
    # Validate measurement_type choice
    if args.measurement_type not in ["full_swing", "interferometry"]:
        parser.error(f"--measurement_type must be 'full_swing' or 'interferometry', got '{args.measurement_type}'")
    
    return args


def main() -> None:
    args = parse_args()
    end_dt = dt.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
    measurement_type = args.measurement_type
    data_prefix = "full_swing" if measurement_type == "full_swing" else "v_meas"
    
    # Record start time for logging
    start_time = dt.datetime.now()
    start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Load existing log and append new entry
    log_data = load_log()
    log_entry = {
        "start_time": start_time_str,
        "measurement_type": measurement_type,
        "description": args.description,
        "Success": False,
    }
    log_data[start_time_str] = log_entry
    save_log(log_data)



    with dwf.Device() as device:
        scope = device.analog_input
        scope[0].setup(range=CHANNEL_RANGE)

        capture_idx = 0
        while dt.datetime.now() <= end_dt:
            # Timestamp for filenames and logs
            measurement_timestamp = t.strftime("%Y%m%d-%H%M%S")
            measurement_time_str = t.strftime("%Y-%m-%d %H:%M:%S")

            print(f"[{measurement_time_str}] Capture {capture_idx} starting")

            # Single capture
            scope.single(sample_rate=F_SAMPLE, buffer_size=BUFFER_SIZE, configure=True, start=True)

            # Read data and timing info
            v_meas = scope[0].get_data()
            sec_utc, trigger_tick, ticks_per_second = scope.time
            time_array = np.arange(len(v_meas)) / F_SAMPLE

            # Save JSON in hierarchical date-based directory
            date_dir = get_date_directory()
            filename = date_dir / f"{data_prefix}_{measurement_timestamp}.json"
            payload = {
                "timestamp": measurement_timestamp,
                "measurement_time": measurement_time_str,
                "sec_utc": int(sec_utc),
                "sample_rate_hz": float(F_SAMPLE),
                "measurement_duration_s": float(MEAS_DURATION),
                "buffer_size": int(len(v_meas)),
                "channel_range_v": float(CHANNEL_RANGE),
                "time_s": time_array.tolist(),
                "voltage_data_v": v_meas.tolist(),
                "trigger_tick": int(trigger_tick),
                "ticks_per_second": int(ticks_per_second),
            }
            with open(filename, "w") as f:
                json.dump(payload, f, indent=2)

            print(
                f"  Saved {len(v_meas)} samples to {filename.name} "
                f"(tick={trigger_tick}, tps={ticks_per_second})"
            )

            capture_idx += 1

    # Record end time and log the measurement session
    end_time = dt.datetime.now()
    end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Load existing log and append new entry
    log_data = load_log()
    log_entry = {
        "start_time": start_time_str,
        "end_time": end_time_str,
        "measurement_type": measurement_type,
        "description": args.description,
        "total_captures": capture_idx,
    }
    log_data[start_time_str] = log_entry
    save_log(log_data)
    
    print(f"Done. Total captures: {capture_idx}")
    print(f"Measurement session logged to {LOG_FILE.name}")


if __name__ == "__main__":
    main()

