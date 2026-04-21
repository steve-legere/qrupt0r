import mimetypes
import time
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

RATE_LIMIT_SECONDS = 0.25


def create_message(image_path: Path):
    filename = image_path.name
    subject = f"QR Payload: {filename}"

    # Create MIME container
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    # Add configuration set (IMPORTANT: goes in SES send_raw_email, not headers)
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    html_body = f"""
    <html>
      <body>
        <p>QR Code: {filename}</p>
        <img src="cid:image1">
      </body>
    </html>
    """

    msg_alternative.attach(MIMEText(html_body, "html"))

    # Attach image inline
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


def main():
    session = boto3.Session(profile_name=PROFILE_NAME, region_name=REGION)
    ses = session.client("ses")

    images = sorted(Path(IMAGE_DIR).glob("*.png"))

    print(f"[+] Found {len(images)} images")

    for i, img_path in enumerate(images, start=1):
        raw_email, subject = create_message(img_path)

        try:
            response = ses.send_raw_email(
                Source=FROM_EMAIL,
                Destinations=[TO_EMAIL],
                RawMessage={"Data": raw_email},
                ConfigurationSetName=CONFIG_SET,
            )

            print(f"[{i}/{len(images)}] Sent: {subject}")

        except Exception as e:
            print(f"[!] Failed to send {img_path.name}: {e}")

        time.sleep(RATE_LIMIT_SECONDS)

    print("\n✔ Done sending all emails.")


if __name__ == "__main__":
    main()
