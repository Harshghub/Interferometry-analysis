"""
Run back-to-back measurements until a specified end datetime.

Usage example:
    python measure_until_end.py --end "2025-12-11 15:30:00"

Optional overrides:
    --sample-rate 1000        Sample rate in Hz (default: 1000)
    --duration 8              Measurement duration in seconds (default: 8)
    --channel-range 0.5       Scope channel range (±V) (default: 0.5)
    --results-dir ../results  Output directory (default: ../results)

The script reuses a single Digilent device session and keeps running
measurements (with minimal gap) until wall-clock time exceeds the end
datetime. Each capture is saved to a JSON file following the existing
`v_meas_YYYYMMDD-HHMMSS.json` pattern.
"""

import argparse
import datetime as dt
import json
import time as t
from pathlib import Path

import dwfpy as dwf
import numpy as np

# Defaults match the single-capture demo
DEFAULT_SAMPLE_RATE = 1e3
DEFAULT_DURATION_S = 8.0
DEFAULT_CHANNEL_RANGE_V = 0.5
DEFAULT_RESULTS_DIR = Path("../results")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run measurements until a given end datetime.")
    parser.add_argument(
        "--end",
        required=True,
        help='End datetime (inclusive) in "YYYY-MM-DD HH:MM:SS" format, local time.',
    )
    parser.add_argument("--sample-rate", type=float, default=DEFAULT_SAMPLE_RATE, help="Sample rate in Hz.")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_S, help="Measurement duration in seconds.")
    parser.add_argument(
        "--channel-range",
        type=float,
        default=DEFAULT_CHANNEL_RANGE_V,
        help="Scope channel range (±V).",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory to store measurement JSON files.",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=0.0,
        help="Optional minimum gap between captures in seconds (default: 0).",
    )
    return parser.parse_args()


def make_filename(results_dir: Path, timestamp: str) -> Path:
    return results_dir / f"v_meas_{timestamp}.json"


def save_capture(
    filepath: Path,
    measurement_timestamp: str,
    measurement_time_str: str,
    sec_utc: int,
    sample_rate_hz: float,
    measurement_duration_s: float,
    channel_range_v: float,
    time_array: np.ndarray,
    voltage: np.ndarray,
) -> None:
    data_to_save = {
        "timestamp": measurement_timestamp,
        "measurement_time": measurement_time_str,
        "sec_utc": int(sec_utc),
        "sample_rate_hz": float(sample_rate_hz),
        "measurement_duration_s": float(measurement_duration_s),
        "buffer_size": int(len(voltage)),
        "channel_range_v": float(channel_range_v),
        "time_s": time_array.tolist(),
        "voltage_data_v": voltage.tolist(),
    }
    with open(filepath, "w") as f:
        json.dump(data_to_save, f, indent=2)


def run_capture(
    scope: dwf.AnalogIn,
    sample_rate_hz: float,
    duration_s: float,
    channel_range_v: float,
    results_dir: Path,
) -> Path:
    buffer_size = int(duration_s * sample_rate_hz)

    # Configure channel 0 (extend if you later need channel 1)
    scope[0].setup(range=channel_range_v)

    # Trigger/capture
    scope.single(sample_rate=sample_rate_hz, buffer_size=buffer_size, configure=True, start=True)

    # Retrieve data and timing info
    v_meas = scope[0].get_data()
    sec_utc, trigger_tick, ticks_per_second = scope.time
    time_array = np.arange(len(v_meas)) / sample_rate_hz

    # Build filenames/timestamps
    measurement_timestamp = t.strftime("%Y%m%d-%H%M%S")
    measurement_time_str = t.strftime("%Y-%m-%d %H:%M:%S")
    filepath = make_filename(results_dir, measurement_timestamp)

    save_capture(
        filepath=filepath,
        measurement_timestamp=measurement_timestamp,
        measurement_time_str=measurement_time_str,
        sec_utc=sec_utc,
        sample_rate_hz=sample_rate_hz,
        measurement_duration_s=duration_s,
        channel_range_v=channel_range_v,
        time_array=time_array,
        voltage=v_meas,
    )

    print(
        f"[{measurement_time_str}] Saved {len(v_meas)} samples to {filepath.name} "
        f"(sr={sample_rate_hz} Hz, dur={duration_s}s, range=±{channel_range_v} V, "
        f"trigger_tick={trigger_tick}, ticks_per_second={ticks_per_second})"
    )
    return filepath


def main() -> None:
    args = parse_args()

    end_dt = dt.datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S")
    now = dt.datetime.now()
    if end_dt <= now:
        raise SystemExit(f"End time {end_dt} is not in the future (now={now}).")

    results_dir = args.results_dir
    results_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Starting continuous measurements until {end_dt} "
        f"(sample_rate={args.sample_rate} Hz, duration={args.duration}s, range=±{args.channel_range} V)"
    )

    with dwf.Device() as device:
        scope = device.analog_input

        capture_count = 0
        while True:
            now = dt.datetime.now()
            if now > end_dt:
                print(f"Reached end time {end_dt}. Stopping.")
                break

            # Run one capture
            run_capture(
                scope=scope,
                sample_rate_hz=args.sample_rate,
                duration_s=args.duration,
                channel_range_v=args.channel_range,
                results_dir=results_dir,
            )
            capture_count += 1

            # Optional gap between captures
            if args.min_gap > 0:
                t.sleep(args.min_gap)

        print(f"Completed {capture_count} captures.")


if __name__ == "__main__":
    main()

