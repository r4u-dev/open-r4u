import inspect
from pathlib import Path


def extract_call_path(max_depth: int = 100) -> tuple[str, int] | None:
    """Extract the call path from the first non-library file in the call stack.

    Args:
        max_depth: Maximum number of frames to inspect

    Returns:
        A tuple of (call_path, line_number) where call_path is formatted as
        "<file-path>::<function>" (e.g., "src/main.py::say_hi")

    """
    stack = inspect.stack()

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
