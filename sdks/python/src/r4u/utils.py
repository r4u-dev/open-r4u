import inspect
import os
from dataclasses import dataclass
from pathlib import Path

from async_trace import collect_async_trace
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FrameInfo:
    filename: str
    function: str
    lineno: int


def extract_call_path(
    max_depth: int = 100,
    is_async: bool = False,
) -> tuple[str, int] | None:
    """Extract the call path from the first non-library file in the call stack.

    Args:
        max_depth: Maximum number of frames to inspect

    Returns:
        A tuple of (call_path, line_number) where call_path is formatted as
        "<file-path>::<function>" (e.g., "src/main.py::say_hi")

    """
    if is_async:
        frames = collect_async_trace().get("frames")
        stack = (
            [
                FrameInfo(
                    filename=frame.get("filename"),
                    function=frame.get("name"),
                    lineno=frame.get("line"),
                )
                for frame in frames
                if frame.get("filename")
            ]
            if frames
            else []
        )
    else:
        stack = [
            FrameInfo(frame.filename, frame.function, frame.lineno)
            for frame in inspect.stack()
            if frame.filename
        ]

    # Get site-packages and other library paths to filter out
    import site

    library_paths = set()

    # Add site-packages directories
    for path in site.getsitepackages():
        library_paths.add(Path(path).resolve())

    # Add user site-packages
    user_site = site.getusersitepackages()
    if user_site:
        library_paths.add(Path(user_site).resolve())

    # Add standard library path
    import sysconfig

    stdlib_path = Path(sysconfig.get_path("stdlib")).resolve()
    library_paths.add(stdlib_path)

    # Iterate through the stack frames
    for frame_info in stack[1 : max_depth + 1]:  # Skip the current frame
        file_path = frame_info.filename
        function_name = frame_info.function
        line_number = frame_info.lineno

        # Resolve the file path
        resolved_path = Path(file_path).resolve()

        # Check if this is a library file
        is_library = False
        for lib_path in library_paths:
            try:
                resolved_path.relative_to(lib_path)
                is_library = True
                break
            except ValueError:
                continue

        # Skip library files and files in site-packages
        if is_library or "site-packages" in file_path:
            continue

        # Skip internal Python files
        if file_path.startswith("<") or file_path == "__main__":
            continue

        # Found the first non-library file
        # Try to make the path relative to current working directory
        try:
            relative_path = Path(file_path).relative_to(Path.cwd())
            call_path = f"{relative_path}::{function_name}"
        except ValueError:
            # If not relative to cwd, use the absolute path
            call_path = f"{file_path}::{function_name}"

        return (call_path, line_number)

    return None



def get_project_name() -> str | None:
    """Get the project name from environment variables."""
    return os.getenv("PROJECT_NAME")


SENSITIVE_HEADERS = {
    "authorization",
    "api-key",
    "x-api-key",
    "token",
    "access-token",
    "secret",
    "password",
    "credential",
}


def redact_headers(headers: dict) -> dict:
    """Redact sensitive headers from a dictionary of headers.

    Args:
        headers: Dictionary of headers to redact

    Returns:
        A new dictionary with sensitive headers redacted.
        The keys are preserved in their original case, but matching is case-insensitive.
    """
    if not headers:
        return {}

    redacted = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted
