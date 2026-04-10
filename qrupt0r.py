# Based on research by Kuo-Chien Chou and Ran-Zan Wang
# "Dual-Message QR Codes" - https://doi.org/10.3390/s24103055
import logging
import os
import sys
from urllib.parse import urlparse

MIN_PYTHON = (3, 9)

if sys.version_info < MIN_PYTHON:
    sys.exit(f"Python %s.%s or later is required.\n" % MIN_PYTHON)

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

from logger import setup_logging, logger

NAME = "qrupt0r"
VERSION = "1.0.2"
URL = "https://github.com/steve-legere/qrupt0r"

# Upper bound (exclusive) for black pixels
THRESHOLD = 128

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


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return all((parsed.scheme, parsed.netloc))


def is_writable_path(path_str: str) -> bool:
    directory = os.path.dirname(path_str) or "."
    return os.access(directory, os.W_OK)


def create_qr_code(
    text: str, error_level: str, module_size=29, border_size=4, version: int = None
) -> qrcode.QRCode:
    """
    Generates a QR code from the given text and error correction level, with optionally specified border size, module size, and version.

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

    if version and not (1 <= version <= 40):
        raise ValueError(f"Invalid QR code version: {version}")

    qr = qrcode.QRCode(
        version=version,
        error_correction=EC_MAP[error_level],
        box_size=module_size,
        border=border_size,
    )
    qr.add_data(text)
    qr.make(fit=True)
    logger.debug(
        f"Created QR code [v: {version}] [ec: {error_level}] [mod: {module_size}] [border: {border_size}]"
    )
    return qr


def get_pixel_map(
    img: Image.Image, module_size: int, border_modules: int
) -> list[list[int]]:
    """
    Extracts a binary pixel map from an image file representing the QR code modules.

    This function reads a grayscale image of a QR code and converts it into a 2D array
    where each element represents a module (1 for black, 0 for white). The conversion
    is done by checking the center pixel in each module area and determining if the
    brightness is below or above a threshold.

    :param img: An Image object representing a QR code.
    :param module_size: Size of each QR code module in pixels (side length). This determines
        how many pixels are sampled from the image for each module.
    :param border_modules: Number of blank modules around the QR code. These modules are not
        included in the pixel map and act as a buffer to avoid edge effects.

    :return: A 2D list (list of lists) where each element is either 0 or 1, representing
        the binary state of each module in the QR code. The dimensions of this list correspond
        to the number of modules per side (not including the border).
    """
    img = img.convert("L")
    width, height = img.size

    # Ignore border modules on the left
    start = module_size * border_modules
    end_x = width - start

    pixels = img.load()

    # Ignore border modules on the right
    modules_per_side = (end_x - start) // module_size
    pixel_map = []

    for row in range(modules_per_side):
        row_data = []
        for col in range(modules_per_side):
            x0 = start + col * module_size
            y0 = start + row * module_size

            # Get the module's centre pixel
            center_x = x0 + module_size // 2
            center_y = y0 + module_size // 2
            pixel = pixels[center_x, center_y]

            # 1 if black, 0 if white
            row_data.append(1 if pixel < THRESHOLD else 0)

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
    if not map1 or not map1[0] or not map2 or not map2[0]:
        logger.error("Empty QR map in XOR function")
        raise typer.Exit(code=1)

    if (len(map1), len(map1[0])) != (len(map2), len(map2[0])):
        logger.warning(
            "XOR operation on two different QR code sizes will likely break functionality"
        )

    if map1 == map2:
        logger.warning("Overlaying duplicate QR codes")

    rows, cols = len(map1), len(map1[0])
    xor_map = [[map1[r][c] ^ map2[r][c] for c in range(cols)] for r in range(rows)]
    return xor_map


def generate_overlay_qr(
    base_image: Image.Image,
    xor_map: list[list[int]],
    module_size: int,
    submodule_size: int,
    border_modules: int,
    output_path: str,
) -> None:
    """Generates a dual-module QR code by overlaying submodules on a base QR code.

    Creates a QR code with embedded submodules by inverting the color of modules
    where the XOR map indicates a difference. This produces a dual-module QR code
    that can be read differently depending on scanning distance.

    Args:
        base_image: PIL Image object representing the base QR code.
        xor_map: 2D list indicating which modules differ between two QR codes (1 = different, 0 = same).
        module_size: Size of each QR code module in pixels (side length).
        submodule_size: Size of each submodule in pixels (side length).
        border_modules: Number of blank modules around the QR code.
        output_path: Path where the final dual-module QR code will be saved.
    """

    img = base_image.convert("RGB")
    draw = ImageDraw.Draw(img)

    offset = module_size * border_modules
    half_gap = (module_size - submodule_size) // 2

    for r in range(len(xor_map)):
        for c in range(len(xor_map)):
            if xor_map[r][c] == 1:
                x0 = offset + c * module_size + half_gap
                y0 = offset + r * module_size + half_gap
                x1 = x0 + submodule_size
                y1 = y0 + submodule_size

                # Determine original module color (sample center pixel)
                center_x = offset + c * module_size + module_size // 2
                center_y = offset + r * module_size + module_size // 2
                pixel = img.getpixel((center_x, center_y))

                # Average RGB (grayscale)
                if sum(pixel) / 3 < THRESHOLD:
                    color = (255, 255, 255)  # white
                else:
                    color = (0, 0, 0)  # black

                draw.rectangle([x0, y0, x1, y1], fill=color)

    img.save(output_path)


def validate_inputs(
    primary_url,
    overlay_url,
    border_size,
    error_level,
    module_size,
    submodule_size,
    output_path,
):
    """Validates all input parameters for dual-module QR code generation.

    Args:
        primary_url: The primary URL to encode in the base QR code.
        overlay_url: The URL to embed as submodules in the QR code.
        border_size: Number of blank modules around the QR code border.
        error_level: Error correction level ('L', 'M', 'Q', or 'H').
        module_size: Size of each QR code module in pixels.
        submodule_size: Size of each embedded submodule in pixels.
        output_path: File path where the generated QR code will be saved.

    Raises:
        typer.Exit: If any validation check fails, exits with code 1.
    """

    if not is_valid_url(primary_url):
        logger.warning("Primary URL does not appear to be a valid URL")

    if not is_valid_url(overlay_url):
        logger.warning("Overlay URL does not appear to be a valid URL")

    if not isinstance(border_size, int) or border_size < 0:
        logger.error("Border size must be a positive integer or 0")
        raise typer.Exit(code=1)

    if module_size <= submodule_size:
        logger.error("Submodule size must be less than module size")
        raise typer.Exit(code=1)

    if submodule_size > (module_size * 0.5):
        logger.warning("Submodule size > 50% of module size may not function correctly")

    if submodule_size < (module_size * 0.1):
        logger.warning("Submodule size < 10% of module size may not function correctly")

    if not (
        isinstance(error_level, str)
        and len(error_level) == 1
        and error_level.upper() in EC_MAP
    ):
        # safe: .upper() is guarded by isinstance()
        logger.error(f"Invalid error level: {error_level}")
        raise typer.Exit(code=1)

    if not is_writable_path(output_path):
        logger.error(f"Permission denied or invalid output path: {output_path}")
        raise typer.Exit(code=1)


@app.command()
def create(
    primary_url: str = typer.Argument(..., help="Primary URL to generate QR code"),
    overlay_url: str = typer.Argument(..., help="URL to embed into the QR code"),
    border_size: int = typer.Option(
        4, "--border", "-b", min=0, help="Border thickness (number of blank modules)"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
    error_level: str = typer.Option(
        "L", "--error-level", "-e", help="Error correction level (L, M, Q, H)"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force output (may break functionality)"
    ),
    module_size: int = typer.Option(
        29, "--module", "-m", min=7, help="Module size in pixels (side length)"
    ),
    output_path: str = typer.Option(
        "qrupt0r.png", "--output", "-o", help="QR code output path"
    ),
    silent: bool = typer.Option(
        False, "--silent", help="Suppress all output (except critical errors)"
    ),
    submodule_size: int = typer.Option(
        5, "--submodule", "-s", min=1, help="Submodule size in pixels (side length)"
    ),
):
    if debug and silent:
        logger.error("Cannot use --debug and --silent together")
        raise typer.Exit(code=1)

    # Determine log level
    if debug:
        level = logging.DEBUG
    elif silent:
        level = logging.CRITICAL
    else:
        level = logging.INFO

    # Apply configuration
    logger.set_level(level)
    setup_logging(level)

    # Print banner unless silent
    if not silent:
        print_banner()

    if force:
        logger.warning("Force output is enabled - this may break functionality")

    else:
        validate_inputs(
            primary_url,
            overlay_url,
            border_size,
            error_level,
            module_size,
            submodule_size,
            output_path,
        )
        logger.debug("create() passed input validation")
        error_level = error_level.upper()

    qr1 = create_qr_code(primary_url, error_level, module_size, border_size)
    qr2 = create_qr_code(overlay_url, error_level, module_size, border_size)

    # Ensure both QR codes are the same size/version
    if qr1.version != qr2.version:
        version = max(qr1.version, qr2.version)
        logger.debug(f"Normalizing QR code versions to [{version}]")
        qr1 = create_qr_code(
            primary_url, error_level, module_size, border_size, version
        )
        qr2 = create_qr_code(
            overlay_url, error_level, module_size, border_size, version
        )

    base_qr = qr1.make_image().convert("RGB")
    overlay_qr = qr2.make_image().convert("RGB")

    map1 = get_pixel_map(base_qr, module_size, border_size)
    map2 = get_pixel_map(overlay_qr, module_size, border_size)
    difference_map = get_xor_result(map1, map2)
    generate_overlay_qr(
        base_qr,
        difference_map,
        module_size,
        submodule_size,
        border_size,
        output_path,
    )

    logger.info(f"QR code created successfully [{output_path}]")


if __name__ == "__main__":
    app()
