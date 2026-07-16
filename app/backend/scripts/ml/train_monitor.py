#!/usr/bin/env python3
"""
Simple training monitor for CPU/memory usage and log tail.
"""
import argparse
import time
import psutil
from pathlib import Path


def monitor(pid_file: Path, log_file: Path, interval: float = 5.0) -> None:
    if not pid_file.exists():
        print(f"PID file not found: {pid_file}")
        return
    pid = int(pid_file.read_text().strip())

    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"Process {pid} not running")
        return

    print(f"Monitoring PID {pid}. Press Ctrl+C to exit.")
    last_pos = 0
    while True:
        try:
            cpu = p.cpu_percent(interval=None)
            mem = p.memory_info().rss / (1024 * 1024)
            children = p.children(recursive=True)
            child_cpu = sum(c.cpu_percent(interval=None) for c in children)
            child_mem = sum(c.memory_info().rss for c in children) / (1024 * 1024)
            print(f"CPU: {cpu + child_cpu:.1f}%  MEM: {mem + child_mem:.1f} MB  Threads: {p.num_threads()}  Children: {len(children)}")

            if log_file.exists():
                with log_file.open("r") as f:
                    f.seek(last_pos)
                    lines = f.readlines()[-10:]
                    last_pos = f.tell()
                    for line in lines:
                        print(line.rstrip())
            time.sleep(interval)
        except KeyboardInterrupt:
            print("Exiting monitor.")
            break


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid-file", default="logs/train_short_lstm.pid")
    ap.add_argument("--log-file", default="logs/train_short_lstm.out")
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()
    monitor(Path(args.pid_file), Path(args.log_file), args.interval)


