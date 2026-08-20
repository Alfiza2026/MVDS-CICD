"""Collect deployment metrics and append to results/metrics.csv.

Usage:
    python scripts/collect_metrics.py \
        --trial-id T01 \
        --condition automated \
        --start-time 1700000000.0 \
        --end-time 1700000045.0 \
        --pytest-result results/pytest-output.xml
"""

import argparse
import csv
import os
import sys
import time
import xml.etree.ElementTree as ET


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
CSV_PATH = os.path.join(RESULTS_DIR, "metrics.csv")

CSV_COLUMNS = [
    "trial_id",
    "condition",
    "deployment_time_seconds",
    "success",
    "failure_category",
    "cpu_peak_mb",
    "mem_peak_mb",
]


def ensure_csv_exists():
    """Create results directory and CSV with headers if not present."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)


def parse_pytest_results(pytest_xml_path):
    """Parse pytest JUnit XML to determine success and failure category."""
    if not pytest_xml_path or not os.path.exists(pytest_xml_path):
        return True, "none"

    try:
        tree = ET.parse(pytest_xml_path)
        root = tree.getroot()

        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))

        if failures == 0 and errors == 0:
            return True, "none"

        # Determine failure category from first failure
        for testcase in root.iter("testcase"):
            failure = testcase.find("failure")
            if failure is not None:
                message = failure.attrib.get("message", "")
                if "assert" in message.lower():
                    return False, "assertion_error"
                elif "timeout" in message.lower():
                    return False, "timeout"
                elif "connection" in message.lower():
                    return False, "connection_error"
                else:
                    return False, "test_failure"
            error = testcase.find("error")
            if error is not None:
                return False, "runtime_error"

        return False, "unknown"
    except Exception:
        return True, "parse_error"


def get_resource_usage():
    """Get peak CPU and memory usage from kubectl top if available."""
    cpu_peak = 0.0
    mem_peak = 0.0

    try:
        import subprocess
        result = subprocess.run(
            ["kubectl", "top", "pods", "-n", "mvds", "--no-headers"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 3:
                    cpu_str = parts[1].replace("m", "")
                    mem_str = parts[2].replace("Mi", "")
                    try:
                        cpu_peak = max(cpu_peak, float(cpu_str))
                        mem_peak = max(mem_peak, float(mem_str))
                    except ValueError:
                        pass
    except Exception:
        pass

    return round(cpu_peak, 2), round(mem_peak, 2)


def main():
    parser = argparse.ArgumentParser(description="Collect deployment metrics")
    parser.add_argument("--trial-id", required=True, help="Unique trial identifier")
    parser.add_argument("--condition", required=True, choices=["automated", "manual"],
                        help="Deployment condition")
    parser.add_argument("--start-time", required=True, type=float,
                        help="Deployment start timestamp (epoch seconds)")
    parser.add_argument("--end-time", required=True, type=float,
                        help="Deployment end timestamp (epoch seconds)")
    parser.add_argument("--pytest-result", default=None,
                        help="Path to pytest JUnit XML output")
    args = parser.parse_args()

    deployment_time = round(args.end_time - args.start_time, 2)
    success, failure_category = parse_pytest_results(args.pytest_result)
    cpu_peak, mem_peak = get_resource_usage()

    ensure_csv_exists()

    row = [
        args.trial_id,
        args.condition,
        deployment_time,
        success,
        failure_category,
        cpu_peak,
        mem_peak,
    ]

    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    print(f"Metrics recorded for trial {args.trial_id}:")
    print(f"  Condition: {args.condition}")
    print(f"  Deployment time: {deployment_time}s")
    print(f"  Success: {success}")
    print(f"  Failure category: {failure_category}")
    print(f"  CPU peak: {cpu_peak}m")
    print(f"  Memory peak: {mem_peak}Mi")


if __name__ == "__main__":
    main()
