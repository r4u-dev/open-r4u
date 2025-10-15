"""Improved utility functions for R4U SDK."""

import inspect
import os
from typing import Tuple, Optional, Set, List
from dataclasses import dataclass


@dataclass
class FrameInfo:
    """Information about a stack frame."""
    filename: str
    function_name: str
    line_number: int
    is_internal: bool
    is_integration: bool
    

class CallPathExtractor:
    """
    Extracts call paths from stack frames for tracing.
    
    This class provides a configurable way to extract call paths showing
    where LLM calls originated from in the codebase.
    """
    
    # Files to skip in the call path
    SKIP_FILE_PATTERNS: Set[str] = {
        "utils.py",
        "_pytest",
        "pytest",
        "site-packages",
        "<frozen",
        "runpy",
        "unittest/mock.py",
        "/mock.py",
        "asyncio/",
        "/asyncio/",
        "threading.py",
        "concurrent/futures",
    }
    
    # Functions to skip in the call path
    # Note: <module> is handled specially as a fallback, not skipped entirely
    SKIP_FUNCTIONS: Set[str] = {
        "_patch_method",
        "wrapper",
        "_make_request",
        "_trace_completion",
        "_trace_completion_async",
        "_create_trace_sync",
        "_create_trace_async",
        "pytest_pyfunc_call",
        "run",
        "_bootstrap",
        "_bootstrap_inner",
    }
    
    # Integration-specific method names to capture
    INTEGRATION_METHODS: Set[str] = {
        "create",
        "acreate",
        "completion",
        "chat",
        "generate",  # For future integrations
        "invoke",
        "ainvoke",
    }
    
    # Patterns that identify integration layer code
    INTEGRATION_PATTERNS: Set[str] = {
        "r4u/integrations",
        "integrations/openai.py",
        "integrations/anthropic.py",
        "integrations/cohere.py",
    }
    
    def __init__(self, max_depth: int = 50, include_cross_file: bool = False):
        """
        Initialize the call path extractor.
        
        Args:
            max_depth: Maximum number of frames to process
            include_cross_file: If True, include calls across multiple files
        """
        self.max_depth = max_depth
        self.include_cross_file = include_cross_file
    
    def _should_skip_frame(self, filename: str, function_name: str) -> bool:
        """Check if a frame should be skipped."""
        if function_name in self.SKIP_FUNCTIONS:
            return True
        return any(pattern in filename for pattern in self.SKIP_FILE_PATTERNS)
    
    def _is_integration_frame(self, filename: str) -> bool:
        """Check if a frame is part of the integration layer."""
        return any(pattern in filename for pattern in self.INTEGRATION_PATTERNS)
    
    def _is_integration_method(self, function_name: str) -> bool:
        """Check if a function name is an integration method we want to capture."""
        return function_name in self.INTEGRATION_METHODS
    
    def _classify_frame(self, frame) -> Optional[FrameInfo]:
        """
        Classify a stack frame.
        
        Returns:
            FrameInfo if frame should be processed, None if it should be skipped
        """
        frame_info = inspect.getframeinfo(frame)
        filename = frame_info.filename
        function_name = frame.f_code.co_name
        
        if self._should_skip_frame(filename, function_name):
            return None
        
        return FrameInfo(
            filename=filename,
            function_name=function_name,
            line_number=frame_info.lineno,
            is_internal=False,
            is_integration=self._is_integration_frame(filename)
        )
    
    def _get_relative_path(self, absolute_path: str) -> str:
        """Convert absolute path to relative path from cwd."""
        try:
            cwd = os.getcwd()
            if absolute_path.startswith(cwd):
                return os.path.relpath(absolute_path, cwd)
        except (ValueError, OSError):
            pass
        return absolute_path
    
    def _collect_frames(self, start_frame) -> List[FrameInfo]:
        """
        Collect relevant frames from the stack.
        
        Returns:
            List of FrameInfo objects in order from outermost to innermost
        """
        frames = []
        current_frame = start_frame
        depth = 0
        
        while current_frame is not None and depth < self.max_depth:
            frame_info = self._classify_frame(current_frame)
            if frame_info is not None:
                frames.append(frame_info)
            
            current_frame = current_frame.f_back
            depth += 1
        
        # Reverse to get outermost to innermost order
        frames.reverse()
        return frames
    
    def _build_path(self, frames: List[FrameInfo]) -> Tuple[str, int]:
        """
        Build the call path string from collected frames.
        
        Returns:
            Tuple of (path_string, line_number)
        """
        if not frames:
            return "unknown", 0
        
        # Find the target file (first non-integration user frame)
        target_frame = None
        for frame in frames:
            if not frame.is_integration:
                target_frame = frame
                break
        
        if target_frame is None:
            return "unknown", 0
        
        # Collect function calls
        function_chain = []
        target_file = target_frame.filename
        module_level_frame = None
        
        for frame in frames:
            # Add integration methods (like "create")
            if frame.is_integration and self._is_integration_method(frame.function_name):
                function_chain.append(frame.function_name)
            # Add functions from target file (or all files if cross-file enabled)
            elif frame.filename == target_file or self.include_cross_file:
                if not frame.is_integration:
                    # Track module-level frame separately
                    if frame.function_name == "<module>":
                        module_level_frame = frame
                    else:
                        function_chain.append(frame.function_name)
        
        # Build the signature
        relative_path = self._get_relative_path(target_file)
        
        if function_chain:
            signature = f"{relative_path}::{function_chain[0]}"
            if len(function_chain) > 1:
                signature += "->" + "->".join(function_chain[1:])
        elif module_level_frame:
            # Use module-level as fallback for calls made at module scope
            signature = relative_path + "::create"
        else:
            signature = relative_path
        
        return signature, target_frame.line_number
    
    def extract(self) -> Tuple[str, int]:
        """
        Extract the call path from the current stack.
        
        Returns:
            Tuple[str, int]: (call_path, line_number)
            
        Example:
            >>> extractor = CallPathExtractor()
            >>> path, line = extractor.extract()
            >>> print(path)
            "src/main.py::main->query_llm->create"
        """
        frame = inspect.currentframe()
        
        try:
            # Skip the extract() and __init__ frames
            if frame is not None:
                frame = frame.f_back  # Skip extract()
            if frame is not None:
                frame = frame.f_back  # Skip extract_call_path() wrapper
            
            if frame is None:
                return "unknown", 0
            
            frames = self._collect_frames(frame)
            return self._build_path(frames)
        
        finally:
            del frame


# Convenience function to maintain backward compatibility
def extract_call_path(max_depth: int = 100) -> Tuple[str, int]:
    """
    Extract the call path from the current stack frame.
    
    This is a convenience wrapper around CallPathExtractor for backward compatibility.
    
    Args:
        max_depth: Maximum number of frames to process
    
    Returns:
        Tuple[str, int]: (call_path, line_number)
        
    Example:
        >>> path, line = extract_call_path()
        >>> print(path)
        "src/main.py::main->query_llm->create"
    """
    extractor = CallPathExtractor(max_depth=max_depth)
    return extractor.extract()
