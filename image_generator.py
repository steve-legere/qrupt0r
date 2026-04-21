import subprocess
import sys
from pathlib import Path

BENIGN_FILE = "./res/benign-urls.txt"
MALICIOUS_FILE = "./res/malicious-urls.txt"
OUTPUT_DIR = "./test/"
QRC_SCRIPT = "./qrupt0r.py"


def load_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def run_qr(output_name, left, right):
    output_path = Path(OUTPUT_DIR) / output_name

    cmd = [
        sys.executable,  # ensures venv Python is used
        QRC_SCRIPT,
        "-o",
        str(output_path),
        "--silent",
        left,
        right,
    ]

    subprocess.run(cmd, check=True)


def main():
    benign = load_lines(BENIGN_FILE)
    malicious = load_lines(MALICIOUS_FILE)

    if len(benign) != len(malicious):
        raise ValueError(
            "Benign and malicious files must have the same number of lines."
        )

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    count = 0

    for i, (b, m) in enumerate(zip(benign, malicious), start=1):

        combos = [
            ("benign_benign", b, b),
            ("malicious_malicious", m, m),
            ("benign_malicious", b, m),
            ("malicious_benign", m, b),
        ]

        for suffix, left, right in combos:
            filename = f"qr_{i:03d}_{suffix}.png"
            print(f"[+] Generating {filename}")

            try:
                run_qr(filename, left, right)
                count += 1
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed: {filename} ({e})")

    print(f"\nDone. Generated {count} QR codes in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
