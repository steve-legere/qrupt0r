import mimetypes
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import boto3

# === CONFIG ===
REGION = "us-east-2"
FROM_EMAIL = ""
TO_EMAIL = ""
PROFILE_NAME = "ses-sender"

IMAGE_DIR = "./test/"
CONFIG_SET = "default_config_set"

# Performance tuning
MAX_WORKERS = 8
MAX_EMAILS_PER_SECOND = 10


# =========================
# TOKEN BUCKET RATE LIMITER
# =========================
class RateLimiter:
    def __init__(self, rate_per_sec: float):
        self.interval = 1.0 / rate_per_sec
        self.lock = threading.Lock()
        self.last_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_time

            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)

            self.last_time = time.time()


rate_limiter = RateLimiter(MAX_EMAILS_PER_SECOND)


def create_message(image_path: Path):
    filename = image_path.name
    subject = f"QR Payload: {filename}"

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    html_body = f"""
    <html>
      <body>
        <p>QR Code: {filename}</p>
        <img src="cid:image1">
      </body>
    </html>
    """

    alt.attach(MIMEText(html_body, "html"))

    with open(image_path, "rb") as f:
        img_data = f.read()

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"

    img = MIMEImage(img_data, _subtype=mime_type.split("/")[1])
    img.add_header("Content-ID", "<image1>")
    img.add_header("Content-Disposition", "inline", filename=filename)

    msg.attach(img)

    return msg.as_string(), subject


def worker(ses, image_path):
    raw_email, subject = create_message(image_path)

    # 🔒 global rate limit (critical)
    rate_limiter.wait()

    response = ses.send_raw_email(
        Source=FROM_EMAIL,
        Destinations=[TO_EMAIL],
        RawMessage={"Data": raw_email},
        ConfigurationSetName=CONFIG_SET,
    )

    return subject, response


def main():
    session = boto3.Session(profile_name=PROFILE_NAME, region_name=REGION)
    ses = session.client("ses")

    images = sorted(Path(IMAGE_DIR).glob("*.png"))
    print(f"[+] Found {len(images)} images")

    sent = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(worker, ses, img): img for img in images}

        for i, future in enumerate(as_completed(futures), start=1):
            img_path = futures[future]

            try:
                subject, _ = future.result()
                sent += 1
                print(f"[{i}/{len(images)}] Sent: {subject}")

            except Exception as e:
                print(f"[!] Failed {img_path.name}: {e}")

    print(f"\n✔ Done. Sent {sent}/{len(images)} emails.")


if __name__ == "__main__":
    main()
