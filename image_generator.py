import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BENIGN_FILE = "./res/benign.txt"
MALICIOUS_FILE = "./res/malicious.txt"
OUTPUT_DIR = "./test/"
QRC_SCRIPT = "./qrupt0r.py"

MAX_WORKERS = 8  # tweak this (start with 4–8)


def load_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def run_qr(output_name, left, right):
    output_path = Path(OUTPUT_DIR) / output_name

    cmd = [
        sys.executable,
        QRC_SCRIPT,
        "-o",
        str(output_path),
        "--silent",
        left,
        right,
    ]

    subprocess.run(cmd, check=True)


def build_tasks(benign, malicious):
    tasks = []

    for i, (b, m) in enumerate(zip(benign, malicious), start=1):
        tasks.extend(
            [
                (f"qr_{i:04d}_benign_benign.png", b, b),
                (f"qr_{i:04d}_malicious_malicious.png", m, m),
                (f"qr_{i:04d}_benign_malicious.png", b, m),
                (f"qr_{i:04d}_malicious_benign.png", m, b),
            ]
        )

    return tasks


def main():
    benign = load_lines(BENIGN_FILE)
    malicious = load_lines(MALICIOUS_FILE)

    if len(benign) != len(malicious):
        raise ValueError(
            "Benign and malicious files must have the same number of lines."
        )

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    tasks = build_tasks(benign, malicious)

    count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_task = {
            executor.submit(run_qr, filename, left, right): filename
            for filename, left, right in tasks
        }

        for future in as_completed(future_to_task):
            filename = future_to_task[future]
            try:
                future.result()
                count += 1
                print(f"[+] Done: {filename}")
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed: {filename} ({e})")

    print(f"\nDone. Generated {count} QR codes in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
