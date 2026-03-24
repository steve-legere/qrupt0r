# Based on research by Kuo-Chien Chou and Ran-Zan Wang
# "Dual-Message QR Codes" - https://doi.org/10.3390/s24103055

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

NAME = "qrupt0r"
VERSION = "0.1.4"
URL = "https://github.com/steve-legere/qrupt0r"

# Reference: https://www.qrcode.com/en/about/error_correction.html
EC_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


app = typer.Typer(add_completion=False)


def print_banner():
    """Prints the CLI banner"""
    banner_text = pyfiglet.figlet_format(NAME, font="smslant")
    typer.secho(banner_text, fg=typer.colors.RED, bold=True)
    typer.secho(f"v{VERSION} :: dual-module QR generator", fg=typer.colors.BRIGHT_BLACK)
    typer.secho(URL + "\n", fg=typer.colors.BRIGHT_BLACK)


def create_qr_code(
    text: str, error_level: str, module_size=29, border_size=4, version: int = None
) -> qrcode.QRCode:
    """
    Generates a QR code from the given text and error correction level, with optionally specified module size, version,
    and border size.

    :param border_size: The number of blank (white) modules around the QR code.
    :param module_size: The side length of each module, in pixels.
    :param text: The data to be encoded in the QR code. Must be a string.
    :param error_level: The error correction level for the QR code. Valid values are 'L', 'M', 'Q', or 'H'.
        This maps to the corresponding error correction strength, per the QR code standard
        (see https://www.qrcode.com/en/about/error_correction.html)
    :param version: Optional version number of the QR code (1-40). If not specified, a suitable version is automatically
    chosen based on the text length.

    :return: A `qrcode.QRCode` object configured with the provided parameters and ready to be rendered or exported.

    :raises ValueError: If an invalid error correction level is provided.
    """
    if error_level not in EC_MAP:
        raise ValueError(f"Invalid error correction level: {error_level}")

    if version and version > 40:
        raise ValueError(f"Invalid QR code version: {version}")

    qr = qrcode.QRCode(
        version=version,
        error_correction=EC_MAP[error_level],
        box_size=module_size,
        border=border_size,
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr


def is_black(module_pixels):
    """Determine if a module is black or white based on average brightness."""
    # Convert to grayscale and average pixel values
    avg = sum(module_pixels) / len(module_pixels)
    return avg < 128  # threshold


def get_pixel_map(
    image_path: str, module_size: int, border_modules: int
) -> list[list[int]]:
    """
    Extracts a binary pixel map from an image file representing the QR code modules.

    This function reads a grayscale image of a QR code and converts it into a 2D array
    where each element represents a module (1 for black, 0 for white). The conversion
    is done by sampling pixels in each module area and determining if the average
    brightness is below or above a threshold.

    :param image_path: Path to the input image file containing the QR code. Must be a valid
        path to an existing file that can be opened with PIL.
    :param module_size: Size of each QR code module in pixels (side length). This determines
        how many pixels are sampled from the image for each module.
    :param border_modules: Number of blank modules around the QR code. These modules are not
        included in the pixel map and act as a buffer to avoid edge effects.

    :return: A 2D list (list of lists) where each element is either 0 or 1, representing
        the binary state of each module in the QR code. The dimensions of this list correspond
        to the number of modules per side (not including the border).
    """
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


def get_xor_result(map1: list[list[int]], map2: list[list[int]]) -> list[list[int]]:
    """Computes the XOR (exclusive OR) of two QR code module maps.

    Args:
        map1: A 2D list representing the first QR code's modules (0 for white, 1 for black).
        map2: A 2D list representing the second QR code's modules (0 for white, 1 for black).

    Returns:
        A 2D list where each element is the XOR of corresponding elements from `map1` and `map2`.
        This results in a binary map that highlights the differences between the two input maps.
    """
    size = len(map1)
    return [[map1[r][c] ^ map2[r][c] for c in range(size)] for r in range(size)]


def generate_overlay_qr(
    base_image_path, xor_map, module_size, submodule_size, border_modules, output_path
):

    img = Image.open(base_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    sub_size = submodule_size
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
    primary_url: str = typer.Argument(..., help="Primary URL to generate QR code"),
    overlay_url: str = typer.Argument(..., help="URL to embed into the QR code"),
    error_level: str = typer.Option(
        "L", "--error-level", "-e", help="Error correction level (L, M, Q, H)"
    ),
    module_size: int = typer.Option(
        29, "--module", "-m", help="Module size in pixels (side length)"
    ),
    submodule_size: int = typer.Option(
        5, "--submodule", "-s", help="Submodule size in pixels (side length)"
    ),
    border_size: int = typer.Option(
        4, "--border", "-b", help="Border thickness (number of blank modules)"
    ),
):
    if submodule_size > module_size:
        typer.secho("Error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.echo("Submodule size must be less than module size")
        raise typer.Exit(code=1)

    error_level = error_level.upper()
    if error_level not in EC_MAP:
        typer.secho("Error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.echo(
            f"Error level must be one of: {[letter for letter in EC_MAP.keys()]}"
        )
        raise typer.Exit(code=1)

    qr1 = create_qr_code(primary_url, error_level, module_size, border_size)
    qr2 = create_qr_code(overlay_url, error_level, module_size, border_size)

    # Ensure both QR codes are the same size/version
    if qr1.version != qr2.version:
        version = max(qr1.version, qr2.version)
        qr1 = create_qr_code(
            primary_url, error_level, module_size, border_size, version
        )
        qr2 = create_qr_code(
            overlay_url, error_level, module_size, border_size, version
        )

    img1 = qr1.make_image()
    img1.save("qr1.png")
    img2 = qr2.make_image()
    img2.save("qr2.png")

    if qr1.version != qr2.version:
        typer.secho("Error: ", fg=typer.colors.RED, bold=True, nl=False)
        typer.echo("QR codes must be the same version/size")
        raise typer.Exit(code=1)

    map1 = get_pixel_map("./qr1.png", module_size, border_size)
    map2 = get_pixel_map("./qr2.png", module_size, border_size)
    difference_map = get_xor_result(map1, map2)
    generate_overlay_qr(
        "./qr1.png",
        difference_map,
        module_size,
        submodule_size,
        border_size,
        "./combined.png",
    )


if __name__ == "__main__":
    print_banner()
    app()
