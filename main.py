import qrcode
import typer
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)

EC_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}

app = typer.Typer(add_completion=False)


def create_qr_code(text: str, error_level: str) -> qrcode.QRCode:
    if error_level not in EC_MAP:
        raise ValueError(f"Invalid error correction level: {error_level}")

    qr = qrcode.QRCode(
        version=None, error_correction=EC_MAP[error_level], box_size=10, border=4
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr


@app.command()
def create(
    primary: str = typer.Argument(..., help="Primary (base) URL to encode as QR code"),
    secondary: str = typer.Argument(..., help="Secondary URL to embed in QR code"),
    error_level: str = typer.Option(
        "L", "--error-level", "-e", help="Error correction level (L, M, Q, H)"
    ),
):
    qr1 = create_qr_code(primary, error_level)
    qr2 = create_qr_code(secondary, error_level)
    img1 = qr1.make_image()
    img1.save("qr1.png")
    img2 = qr2.make_image()
    img2.save("qr2.png")
    print(f"Got QR code versions: {qr1.version} and {qr2.version}")


if __name__ == "__main__":
    app()
