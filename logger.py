import logging

import typer

LOG_STYLES = {
    logging.DEBUG: {"symbol": "[D]", "fg": typer.colors.BRIGHT_YELLOW, "bold": True},
    logging.INFO: {"symbol": "[*]", "fg": typer.colors.BLUE, "bold": True},
    logging.WARNING: {"symbol": "[!]", "fg": typer.colors.YELLOW, "bold": True},
    logging.ERROR: {"symbol": "[X]", "fg": typer.colors.RED, "bold": True},
    logging.CRITICAL: {"symbol": "[!!]", "fg": typer.colors.RED, "bold": True},
}


class Logger:
    def __init__(self, level: int = logging.INFO):
        self.level = level

    def set_level(self, level: int):
        self.level = level

    def log(self, level: int, message: str):
        """Public log method using standard logging levels."""
        if level < self.level:
            return

        style = LOG_STYLES.get(level, {})
        symbol = style.get("symbol", "[ ]")

        typer.secho(
            f"{symbol} ",
            fg=style.get("fg"),
            bold=style.get("bold", False),
            nl=False,
        )

        typer.echo(message)

    def __getattr__(self, name: str):
        """
        Dynamically handle logger.debug/info/warning/etc.
        Maps method name → logging level.
        """
        level = getattr(logging, name.upper(), None)

        if not isinstance(level, int):
            raise AttributeError(f"'Logger' object has no attribute '{name}'")

        def method(message: str):
            self.log(level, message)

        return method


logger = Logger()


class TyperHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        level = record.levelno

        style = LOG_STYLES.get(level, {})
        symbol = style.get("symbol", "[ ]")

        typer.secho(
            f"{symbol} {msg}",
            fg=style.get("fg"),
            bold=style.get("bold", False),
        )


def setup_logging(level: int = logging.INFO):
    handler = TyperHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
