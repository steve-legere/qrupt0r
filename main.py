import pyfiglet
import qrcode
import typer
from PIL import Image, ImageDraw
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
NAME = "qrupt0r"
VERSION = "0.0.2"
URL = "https://github.com/steve-legere/qrupt0r"


def print_banner():
    banner_text = pyfiglet.figlet_format(NAME, font="smslant")
    typer.secho(banner_text, fg=typer.colors.RED, bold=True)
    typer.secho(f"v{VERSION} :: dual-module QR generator", fg=typer.colors.BRIGHT_BLACK)
    typer.secho(URL + "\n", fg=typer.colors.BRIGHT_BLACK)


def create_qr_code(text: str, error_level: str) -> qrcode.QRCode:
    if error_level not in EC_MAP:
        raise ValueError(f"Invalid error correction level: {error_level}")

    qr = qrcode.QRCode(
        version=None, error_correction=EC_MAP[error_level], box_size=29, border=4
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def is_black(module_pixels):
    """Determine if a module is black or white based on average brightness."""
    # Convert to grayscale and average pixel values
    avg = sum(module_pixels) / len(module_pixels)
    return avg < 128  # threshold


def get_pixel_map(image_path, module_size, border_modules):
    img = Image.open(image_path).convert("L")  # grayscale
    width, height = img.size

    start = module_size * border_modules
    end_x = width - start

    pixels = img.load()

    modules_per_side = (end_x - start) // module_size
    pixel_map = []

    for row in range(modules_per_side):
        row_data = []
        for col in range(modules_per_side):
            x0 = start + col * module_size
            y0 = start + row * module_size

            # Collect pixels for this module
            module_pixels = [
                pixels[x0 + dx, y0 + dy]
                for dy in range(module_size)
                for dx in range(module_size)
            ]

            row_data.append(1 if is_black(module_pixels) else 0)

        pixel_map.append(row_data)

    return pixel_map


def get_xor_result(map1, map2):
    size = len(map1)
    return [[map1[r][c] ^ map2[r][c] for c in range(size)] for r in range(size)]


def generate_overlay_qr(
    base_image_path, xor_map, module_size, border_modules, output_path
):
    img = Image.open(base_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    sub_size = int(module_size * 0.3)
    offset = module_size * border_modules
    half_gap = (module_size - sub_size) // 2

    for r in range(len(xor_map)):
        for c in range(len(xor_map)):
            if xor_map[r][c] == 1:
                x0 = offset + c * module_size + half_gap
                y0 = offset + r * module_size + half_gap
                x1 = x0 + sub_size
                y1 = y0 + sub_size

                # Determine original module color (sample center pixel)
                center_x = offset + c * module_size + module_size // 2
                center_y = offset + r * module_size + module_size // 2
                pixel = img.getpixel((center_x, center_y))

                # Invert color
                if sum(pixel) / 3 < 128:
                    color = (255, 255, 255)  # white
                else:
                    color = (0, 0, 0)  # black

                draw.rectangle([x0, y0, x1, y1], fill=color)

    img.save(output_path)


@app.command()
def create(
    primary: str = typer.Argument(..., help="Primary (base) URL to encode as QR code"),
    secondary: str = typer.Argument(..., help="Secondary URL to embed in QR code"),
    error_level: str = typer.Option(
        "M", "--error-level", "-e", help="Error correction level (L, M, Q, H)"
    ),
):
    qr1 = create_qr_code(primary, error_level)
    qr2 = create_qr_code(secondary, error_level)
    img1 = qr1.make_image()
    img1.save("qr1.png")
    img2 = qr2.make_image()
    img2.save("qr2.png")
    print(f"Got QR code versions: {qr1.version} and {qr2.version}")

    map1 = get_pixel_map("./qr1.png", 29, 4)
    map2 = get_pixel_map("./qr2.png", 29, 4)
    difference_map = get_xor_result(map1, map2)
    generate_overlay_qr("./qr1.png", difference_map, 29, 4, "./combined.png")


if __name__ == "__main__":
    print_banner()
    app()
