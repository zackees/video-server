"""
Input output.
"""

from pathvalidate import sanitize_filepath


def sanitze_path(path: str) -> str:
    """Sanitizes a path."""
    return str(
        sanitize_filepath(path)  # type: ignore
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
        .replace("-", "_")
        .replace(",", "_")
        .replace(":", "_")
        .replace(";", "_")
        .replace("(", "_")
        .replace(")", "_")
        .replace("[", "_")
        .replace("]", "_")
        .replace("{", "_")
        .replace("}", "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("?", "_")
        .replace("!", "_")
        .replace("@", "_")
        .replace("#", "_")
        .replace("$", "_")
        .replace("%", "_")
        .replace("^", "_")
        .replace("&", "_")
        .replace("*", "_")
        .replace("+", "_")
        .replace("=", "_")
        .replace("|", "_")
        .replace("~", "_")
        .replace("`", "_")
        .replace("'", "_")
        .replace('"', "_")
        .replace(" ", "_")
        .replace("\t", "_")
        .replace("\n", "_")
        .replace("\r", "_")
    )


def read_utf8(file: str) -> str:
    """Reads a file and returns its contents as a string."""
    with open(file, encoding="utf-8", mode="r") as f:  # pylint: disable=invalid-name
        return f.read()


def write_utf8(file: str, contents: str) -> None:
    """Writes a string to a file."""
    with open(file, encoding="utf-8", mode="w") as f:  # pylint: disable=invalid-name
        f.write(contents)