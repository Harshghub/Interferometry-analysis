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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run measurements until the specified end datetime.")
    parser.add_argument(
        "--end",
        required=True,
        help='End datetime (inclusive) in "YYYY-MM-DD HH:MM:SS" (local time).',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    end_dt = dt.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")

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

            # Save JSON
            filename = RESULTS_DIR / f"v_meas_{measurement_timestamp}.json"
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

    print(f"Done. Total captures: {capture_idx}")


if __name__ == "__main__":
    main()

