#!/usr/bin/env python3
"""
Enhanced file tracing example showing how to improve R4U's HTTP tracing
to better capture and analyze file upload data.

This example demonstrates:
1. How to enhance the current tracing system for file uploads
2. File metadata extraction from multipart data
3. File content analysis and type detection
4. Integration with the existing R4U tracing infrastructure
"""

import base64
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from r4u.tracing.http.tracer import RawRequestInfo
from r4u.client import R4UClient, HTTPTrace


@dataclass
class FileInfo:
    """Information about a file in an HTTP request."""
    filename: Optional[str] = None
    field_name: Optional[str] = None
    content_type: Optional[str] = None
    size: int = 0
    file_type: Optional[str] = None
    content_preview: Optional[str] = None
    is_binary: bool = False


class EnhancedFileTracer:
    """Enhanced tracer that specifically handles file uploads and extracts file metadata."""
    
    def __init__(self, r4u_client: R4UClient):
        self._r4u_client = r4u_client
        self.file_analysis_enabled = True
    
    def trace_request(self, request_info: RawRequestInfo) -> None:
        """Enhanced tracing with file upload analysis."""
        
        # Check if this request contains files
        if self.file_analysis_enabled and self._is_file_upload(request_info):
            file_info = self._analyze_file_upload(request_info)
            if file_info:
                # Add file information to metadata
                if not hasattr(request_info, 'file_metadata'):
                    request_info.file_metadata = file_info
                else:
                    request_info.file_metadata.update(file_info)
        
        # Call parent implementation
        super().trace_request(request_info)
    
    def _is_file_upload(self, request_info: RawRequestInfo) -> bool:
        """Detect if this request contains file uploads."""
        content_type = request_info.headers.get('content-type', '').lower()
        
        # Check for multipart/form-data
        if 'multipart/form-data' in content_type:
            return True
        
        # Check for file-related content types
        file_indicators = [
            'application/octet-stream',
            'image/', 'video/', 'audio/',
            'text/plain', 'application/pdf',
            'application/zip', 'application/x-zip'
        ]
        
        return any(indicator in content_type for indicator in file_indicators)
    
    def _analyze_file_upload(self, request_info: RawRequestInfo) -> Optional[Dict[str, Any]]:
        """Analyze file upload and extract metadata."""
        content_type = request_info.headers.get('content-type', '')
        
        if 'multipart/form-data' in content_type:
            return self._analyze_multipart_upload(request_info)
        else:
            return self._analyze_binary_upload(request_info)
    
    def _analyze_multipart_upload(self, request_info: RawRequestInfo) -> Optional[Dict[str, Any]]:
        """Analyze multipart/form-data upload."""
        try:
            content_type = request_info.headers.get('content-type', '')
            
            # Extract boundary
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part.split('=', 1)[1].strip('"')
                    break
            
            if not boundary:
                return None
            
            # Parse multipart data
            boundary_bytes = f'--{boundary}'.encode()
            parts = request_info.request_payload.split(boundary_bytes)
            
            files_info = []
            form_fields = []
            
            for part in parts[1:-1]:  # Skip first and last empty parts
                if not part.strip():
                    continue
                
                file_info = self._parse_multipart_part(part)
                if file_info:
                    if file_info.filename:
                        files_info.append(file_info)
                    else:
                        form_fields.append(file_info)
            
            return {
                'upload_type': 'multipart',
                'files': [self._file_info_to_dict(f) for f in files_info],
                'form_fields': [self._file_info_to_dict(f) for f in form_fields],
                'total_files': len(files_info),
                'total_size': sum(f.size for f in files_info)
            }
            
        except Exception as e:
            print(f"Error analyzing multipart upload: {e}")
            return None
    
    def _parse_multipart_part(self, part: bytes) -> Optional[FileInfo]:
        """Parse a single part of multipart data."""
        try:
            # Split headers and body
            if b'\r\n\r\n' in part:
                headers_raw, body = part.split(b'\r\n\r\n', 1)
            elif b'\n\n' in part:
                headers_raw, body = part.split(b'\n\n', 1)
            else:
                return None
            
            # Parse headers
            headers = {}
            for line in headers_raw.decode('utf-8', errors='ignore').split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Extract file information
            file_info = FileInfo()
            file_info.size = len(body)
            file_info.content_type = headers.get('content-type', 'unknown')
            
            # Parse Content-Disposition
            content_disposition = headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                # Extract filename
                filename_start = content_disposition.find('filename=') + 9
                filename_end = content_disposition.find(';', filename_start)
                if filename_end == -1:
                    filename_end = len(content_disposition)
                file_info.filename = content_disposition[filename_start:filename_end].strip('"')
            
            if 'name=' in content_disposition:
                # Extract field name
                name_start = content_disposition.find('name=') + 5
                name_end = content_disposition.find(';', name_start)
                if name_end == -1:
                    name_end = len(content_disposition)
                file_info.field_name = content_disposition[name_start:name_end].strip('"')
            
            # Analyze content
            file_info.is_binary = self._is_binary_content(body, file_info.content_type)
            file_info.file_type = self._detect_file_type(body)
            
            # Generate content preview for text files
            if not file_info.is_binary and file_info.size > 0:
                try:
                    preview = body[:200].decode('utf-8', errors='ignore')
                    file_info.content_preview = preview
                except Exception:
                    pass
            
            return file_info
            
        except Exception as e:
            print(f"Error parsing multipart part: {e}")
            return None
    
    def _analyze_binary_upload(self, request_info: RawRequestInfo) -> Optional[Dict[str, Any]]:
        """Analyze binary file upload."""
        payload = request_info.request_payload
        content_type = request_info.headers.get('content-type', 'unknown')
        
        file_info = FileInfo()
        file_info.size = len(payload)
        file_info.content_type = content_type
        file_info.is_binary = True
        file_info.file_type = self._detect_file_type(payload)
        
        # Try to extract filename from headers or URL
        file_info.filename = self._extract_filename_from_headers(request_info.headers)
        
        return {
            'upload_type': 'binary',
            'files': [self._file_info_to_dict(file_info)],
            'total_files': 1,
            'total_size': file_info.size
        }
    
    def _is_binary_content(self, content: bytes, content_type: str) -> bool:
        """Determine if content is binary."""
        # Check content type
        if any(ct in content_type.lower() for ct in ['image/', 'video/', 'audio/', 'application/octet-stream']):
            return True
        
        # Check for null bytes (binary indicator)
        if b'\x00' in content:
            return True
        
        # Try to decode as UTF-8
        try:
            content.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True
    
    def _detect_file_type(self, content: bytes) -> Optional[str]:
        """Detect file type from magic bytes."""
        if len(content) < 4:
            return None
        
        magic_signatures = {
            b'\x89PNG': 'PNG image',
            b'\xff\xd8\xff': 'JPEG image',
            b'GIF8': 'GIF image',
            b'%PDF': 'PDF document',
            b'PK\x03\x04': 'ZIP archive',
            b'\x1f\x8b\x08': 'GZIP archive',
            b'RIFF': 'RIFF container (AVI, WAV, etc.)',
            b'\x00\x00\x01\x00': 'ICO image',
            b'BM': 'BMP image',
        }
        
        for signature, file_type in magic_signatures.items():
            if content.startswith(signature):
                return file_type
        
        return None
    
    def _extract_filename_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract filename from various headers."""
        # Check Content-Disposition
        content_disposition = headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename_start = content_disposition.find('filename=') + 9
            filename_end = content_disposition.find(';', filename_start)
            if filename_end == -1:
                filename_end = len(content_disposition)
            return content_disposition[filename_start:filename_end].strip('"')
        
        # Check X-Filename header
        if 'x-filename' in headers:
            return headers['x-filename']
        
        return None
    
    def _file_info_to_dict(self, file_info: FileInfo) -> Dict[str, Any]:
        """Convert FileInfo to dictionary."""
        return {
            'filename': file_info.filename,
            'field_name': file_info.field_name,
            'content_type': file_info.content_type,
            'size': file_info.size,
            'file_type': file_info.file_type,
            'is_binary': file_info.is_binary,
            'content_preview': file_info.content_preview
        }
    
    def _convert_payload_to_dict(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Enhanced payload conversion with file analysis."""
        if not payload:
            return {"raw": "", "size": 0}
        
        # Check if this is a file upload
        content_type = headers.get("content-type", "").lower()
        
        if 'multipart/form-data' in content_type:
            # For multipart data, provide structured analysis
            return self._convert_multipart_payload(payload, headers)
        elif self._is_binary_content(payload, content_type):
            # For binary data, provide file information
            return self._convert_binary_payload(payload, headers)
        else:
            # For text/JSON data, use parent implementation
            return super()._convert_payload_to_dict(payload, headers)
    
    def _convert_multipart_payload(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Convert multipart payload to structured data."""
        try:
            # Extract boundary
            content_type = headers.get("content-type", "")
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part.split('=', 1)[1].strip('"')
                    break
            
            if not boundary:
                return {"raw": base64.b64encode(payload).decode('utf-8'), "size": len(payload), "encoding": "base64"}
            
            # Parse parts
            boundary_bytes = f'--{boundary}'.encode()
            parts = payload.split(boundary_bytes)
            
            structured_parts = []
            for i, part in enumerate(parts[1:-1]):
                if not part.strip():
                    continue
                
                part_info = self._parse_multipart_part(part)
                if part_info:
                    structured_parts.append({
                        'part_index': i,
                        'filename': part_info.filename,
                        'field_name': part_info.field_name,
                        'content_type': part_info.content_type,
                        'size': part_info.size,
                        'file_type': part_info.file_type,
                        'is_binary': part_info.is_binary,
                        'content_preview': part_info.content_preview
                    })
            
            return {
                "multipart": {
                    "boundary": boundary,
                    "parts": structured_parts,
                    "total_parts": len(structured_parts)
                },
                "size": len(payload),
                "content_type": content_type
            }
            
        except Exception as e:
            print(f"Error converting multipart payload: {e}")
            return {"raw": base64.b64encode(payload).decode('utf-8'), "size": len(payload), "encoding": "base64"}
    
    def _convert_binary_payload(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """Convert binary payload to structured data."""
        file_type = self._detect_file_type(payload)
        filename = self._extract_filename_from_headers(headers)
        
        return {
            "binary": {
                "filename": filename,
                "file_type": file_type,
                "size": len(payload),
                "content_type": headers.get("content-type", "application/octet-stream")
            },
            "raw": base64.b64encode(payload).decode('utf-8'),
            "size": len(payload),
            "encoding": "base64"
        }


def demonstrate_enhanced_tracing():
    """Demonstrate the enhanced file tracing capabilities."""
    print("Enhanced File Tracing Demo")
    print("=" * 40)
    
    # Create a mock R4U client for demonstration
    class MockR4UClient:
        def send(self, trace: HTTPTrace):
            print("\n=== TRACE SENT ===")
            print(f"Endpoint: {trace.endpoint}")
            print(f"Model: {trace.model}")
            print(f"Status: {trace.status_code}")
            print(f"Duration: {trace.duration_ms}ms")
            
            if hasattr(trace, 'request') and trace.request:
                print(f"Request data keys: {list(trace.request.keys())}")
                if 'multipart' in trace.request:
                    print(f"Multipart parts: {trace.request['multipart']['total_parts']}")
                elif 'binary' in trace.request:
                    print(f"Binary file: {trace.request['binary']['filename']}")
            
            if hasattr(trace, 'metadata') and trace.metadata:
                print(f"Metadata: {trace.metadata}")
    
    # Create enhanced tracer
    mock_client = MockR4UClient()
    tracer = EnhancedFileTracer(mock_client)
    
    # Simulate different types of file uploads
    print("\n1. Simulating multipart file upload...")
    
    # Create mock multipart data
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    multipart_data = f"""--{boundary}
Content-Disposition: form-data; name="file"; filename="test.txt"
Content-Type: text/plain

This is a test file content.
It has multiple lines.
--{boundary}
Content-Disposition: form-data; name="description"

File upload test
--{boundary}--""".encode('utf-8')
    
    mock_request = RawRequestInfo(
        method="POST",
        url="https://api.example.com/upload",
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        request_payload=multipart_data,
        request_size=len(multipart_data),
        status_code=200,
        response_payload=b'{"success": true}',
        response_size=17,
        response_headers={"content-type": "application/json"},
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_ms=150.0,
        endpoint="/upload"
    )
    
    tracer.trace_request(mock_request)
    
    print("\n2. Simulating binary file upload...")
    
    # Create mock binary data (PNG header)
    binary_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    
    mock_request_binary = RawRequestInfo(
        method="POST",
        url="https://api.example.com/upload",
        headers={"content-type": "image/png", "x-filename": "test.png"},
        request_payload=binary_data,
        request_size=len(binary_data),
        status_code=200,
        response_payload=b'{"success": true}',
        response_size=17,
        response_headers={"content-type": "application/json"},
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_ms=200.0,
        endpoint="/upload"
    )
    
    tracer.trace_request(mock_request_binary)


if __name__ == "__main__":
    demonstrate_enhanced_tracing()
