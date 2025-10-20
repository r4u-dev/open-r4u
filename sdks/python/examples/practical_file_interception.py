#!/usr/bin/env python3
"""
Practical example of intercepting file uploads in HTTP requests using R4U.

This example shows how to:
1. Set up R4U tracing for file uploads
2. Intercept and analyze file data in real HTTP requests
3. Extract file metadata and content
4. Handle different file upload scenarios
"""

import io
import json
from typing import Dict, Any, List

import requests
from r4u.tracing.http import trace_requests_session
from r4u.tracing.http.tracer import UniversalTracer, RawRequestInfo
from r4u.client import R4UClient


class FileUploadInterceptor:
    """Interceptor for capturing and analyzing file uploads in HTTP requests."""
    
    def __init__(self, r4u_client: R4UClient):
        self.r4u_client = r4u_client
        self.captured_files: List[Dict[str, Any]] = []
        self.tracer = None
    
    def setup_tracing(self, session: requests.Session):
        """Set up enhanced tracing for the session."""
        self.tracer = EnhancedFileTracer(self.r4u_client, "http_requests")
        trace_requests_session(session, self.tracer)
    
    def get_captured_files(self) -> List[Dict[str, Any]]:
        """Get list of captured file uploads."""
        return self.captured_files.copy()
    
    def clear_captured_files(self):
        """Clear the list of captured files."""
        self.captured_files.clear()


class EnhancedFileTracer(UniversalTracer):
    """Enhanced tracer that captures file upload information."""
    
    def __init__(self, r4u_client: R4UClient, provider: str):
        super().__init__(r4u_client, provider)
        self.file_interceptor = None
    
    def set_file_interceptor(self, interceptor: FileUploadInterceptor):
        """Set the file interceptor for capturing file data."""
        self.file_interceptor = interceptor
    
    def trace_request(self, request_info: RawRequestInfo) -> None:
        """Enhanced tracing with file upload capture."""
        
        # Check for file uploads
        if self._is_file_upload(request_info):
            file_data = self._extract_file_data(request_info)
            if file_data and self.file_interceptor:
                self.file_interceptor.captured_files.append(file_data)
        
        # Call parent implementation
        super().trace_request(request_info)
    
    def _is_file_upload(self, request_info: RawRequestInfo) -> bool:
        """Check if request contains file uploads."""
        content_type = request_info.headers.get('content-type', '').lower()
        
        # Multipart form data
        if 'multipart/form-data' in content_type:
            return True
        
        # Binary content types
        binary_types = [
            'application/octet-stream',
            'image/', 'video/', 'audio/',
            'application/pdf', 'application/zip'
        ]
        
        return any(bt in content_type for bt in binary_types)
    
    def _extract_file_data(self, request_info: RawRequestInfo) -> Dict[str, Any]:
        """Extract file data from request."""
        content_type = request_info.headers.get('content-type', '')
        
        if 'multipart/form-data' in content_type:
            return self._extract_multipart_files(request_info)
        else:
            return self._extract_binary_file(request_info)
    
    def _extract_multipart_files(self, request_info: RawRequestInfo) -> Dict[str, Any]:
        """Extract files from multipart form data."""
        try:
            # Extract boundary
            boundary = self._extract_boundary(request_info.headers.get('content-type', ''))
            if not boundary:
                return {}
            
            # Parse multipart data
            boundary_bytes = f'--{boundary}'.encode()
            parts = request_info.request_payload.split(boundary_bytes)
            
            files = []
            form_data = {}
            
            for part in parts[1:-1]:
                if not part.strip():
                    continue
                
                part_info = self._parse_multipart_part(part)
                if part_info:
                    if part_info.get('filename'):
                        files.append(part_info)
                    else:
                        form_data[part_info.get('field_name', 'unknown')] = part_info.get('content', '')
            
            return {
                'type': 'multipart',
                'url': request_info.url,
                'method': request_info.method,
                'timestamp': request_info.started_at.isoformat(),
                'files': files,
                'form_data': form_data,
                'total_size': request_info.request_size
            }
            
        except Exception as e:
            print(f"Error extracting multipart files: {e}")
            return {}
    
    def _extract_binary_file(self, request_info: RawRequestInfo) -> Dict[str, Any]:
        """Extract binary file information."""
        payload = request_info.request_payload
        content_type = request_info.headers.get('content-type', 'unknown')
        
        # Try to detect file type
        file_type = self._detect_file_type(payload)
        
        # Extract filename from headers
        filename = self._extract_filename_from_headers(request_info.headers)
        
        return {
            'type': 'binary',
            'url': request_info.url,
            'method': request_info.method,
            'timestamp': request_info.started_at.isoformat(),
            'filename': filename,
            'content_type': content_type,
            'file_type': file_type,
            'size': len(payload),
            'is_binary': True
        }
    
    def _extract_boundary(self, content_type: str) -> str:
        """Extract boundary from content-type header."""
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                return part.split('=', 1)[1].strip('"')
        return ""
    
    def _parse_multipart_part(self, part: bytes) -> Dict[str, Any]:
        """Parse a single multipart part."""
        try:
            # Split headers and body
            if b'\r\n\r\n' in part:
                headers_raw, body = part.split(b'\r\n\r\n', 1)
            elif b'\n\n' in part:
                headers_raw, body = part.split(b'\n\n', 1)
            else:
                return {}
            
            # Parse headers
            headers = {}
            for line in headers_raw.decode('utf-8', errors='ignore').split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # Extract information
            content_disposition = headers.get('content-disposition', '')
            filename = self._extract_filename_from_content_disposition(content_disposition)
            field_name = self._extract_field_name_from_content_disposition(content_disposition)
            content_type = headers.get('content-type', 'unknown')
            
            # Determine if it's binary
            is_binary = self._is_binary_content(body, content_type)
            
            # Get content preview for text files
            content_preview = None
            if not is_binary and len(body) > 0:
                try:
                    content_preview = body[:200].decode('utf-8', errors='ignore')
                except Exception:
                    pass
            
            return {
                'filename': filename,
                'field_name': field_name,
                'content_type': content_type,
                'size': len(body),
                'is_binary': is_binary,
                'content_preview': content_preview,
                'content': body.decode('utf-8', errors='ignore') if not is_binary else None
            }
            
        except Exception as e:
            print(f"Error parsing multipart part: {e}")
            return {}
    
    def _extract_filename_from_content_disposition(self, content_disposition: str) -> str:
        """Extract filename from Content-Disposition header."""
        if 'filename=' in content_disposition:
            filename_start = content_disposition.find('filename=') + 9
            filename_end = content_disposition.find(';', filename_start)
            if filename_end == -1:
                filename_end = len(content_disposition)
            return content_disposition[filename_start:filename_end].strip('"')
        return ""
    
    def _extract_field_name_from_content_disposition(self, content_disposition: str) -> str:
        """Extract field name from Content-Disposition header."""
        if 'name=' in content_disposition:
            name_start = content_disposition.find('name=') + 5
            name_end = content_disposition.find(';', name_start)
            if name_end == -1:
                name_end = len(content_disposition)
            return content_disposition[name_start:name_end].strip('"')
        return ""
    
    def _extract_filename_from_headers(self, headers: Dict[str, str]) -> str:
        """Extract filename from various headers."""
        # Check Content-Disposition
        content_disposition = headers.get('content-disposition', '')
        if content_disposition:
            filename = self._extract_filename_from_content_disposition(content_disposition)
            if filename:
                return filename
        
        # Check X-Filename
        if 'x-filename' in headers:
            return headers['x-filename']
        
        return ""
    
    def _is_binary_content(self, content: bytes, content_type: str) -> bool:
        """Check if content is binary."""
        # Check content type
        if any(ct in content_type.lower() for ct in ['image/', 'video/', 'audio/', 'application/octet-stream']):
            return True
        
        # Check for null bytes
        if b'\x00' in content:
            return True
        
        # Try to decode as UTF-8
        try:
            content.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True
    
    def _detect_file_type(self, content: bytes) -> str:
        """Detect file type from magic bytes."""
        if len(content) < 4:
            return "unknown"
        
        magic_signatures = {
            b'\x89PNG': 'PNG image',
            b'\xff\xd8\xff': 'JPEG image',
            b'GIF8': 'GIF image',
            b'%PDF': 'PDF document',
            b'PK\x03\x04': 'ZIP archive',
            b'\x1f\x8b\x08': 'GZIP archive',
        }
        
        for signature, file_type in magic_signatures.items():
            if content.startswith(signature):
                return file_type
        
        return "unknown"


def demonstrate_file_interception():
    """Demonstrate file upload interception."""
    print("File Upload Interception Demo")
    print("=" * 40)
    
    # Create a mock R4U client
    class MockR4UClient:
        def send(self, trace):
            print(f"Trace sent: {trace.provider} - {trace.endpoint}")
    
    # Set up interceptor
    mock_client = MockR4UClient()
    interceptor = FileUploadInterceptor(mock_client)
    
    # Create session with tracing
    session = requests.Session()
    interceptor.setup_tracing(session)
    
    # Create test files
    test_files = {
        'text.txt': "This is a test text file.\nIt contains multiple lines.",
        'data.json': json.dumps({"message": "Hello", "data": [1, 2, 3]}, indent=2),
        'binary.png': b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    }
    
    print("\n1. Testing multipart file upload...")
    
    # Test multipart upload
    files = {
        'file': ('test.txt', io.BytesIO(test_files['text.txt'].encode()), 'text/plain')
    }
    data = {'description': 'Test file upload'}
    
    try:
        response = session.post('https://httpbin.org/post', files=files, data=data)
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n2. Testing multiple file upload...")
    
    # Test multiple files
    files = [
        ('files', ('text.txt', io.BytesIO(test_files['text.txt'].encode()), 'text/plain')),
        ('files', ('data.json', io.BytesIO(test_files['data.json'].encode()), 'application/json'))
    ]
    
    try:
        response = session.post('https://httpbin.org/post', files=files)
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n3. Testing binary file upload...")
    
    # Test binary upload
    files = {
        'image': ('test.png', io.BytesIO(test_files['binary.png']), 'image/png')
    }
    
    try:
        response = session.post('https://httpbin.org/post', files=files)
        print(f"Response status: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Show captured files
    print(f"\n=== CAPTURED {len(interceptor.get_captured_files())} FILE UPLOADS ===")
    for i, file_data in enumerate(interceptor.get_captured_files()):
        print(f"\nUpload {i+1}:")
        print(f"  Type: {file_data.get('type', 'unknown')}")
        print(f"  URL: {file_data.get('url', 'unknown')}")
        print(f"  Method: {file_data.get('method', 'unknown')}")
        print(f"  Timestamp: {file_data.get('timestamp', 'unknown')}")
        
        if file_data.get('type') == 'multipart':
            files = file_data.get('files', [])
            print(f"  Files: {len(files)}")
            for j, file_info in enumerate(files):
                print(f"    File {j+1}: {file_info.get('filename', 'unnamed')}")
                print(f"      Size: {file_info.get('size', 0)} bytes")
                print(f"      Type: {file_info.get('content_type', 'unknown')}")
                print(f"      Binary: {file_info.get('is_binary', False)}")
        
        elif file_data.get('type') == 'binary':
            print(f"  Filename: {file_data.get('filename', 'unnamed')}")
            print(f"  Size: {file_data.get('size', 0)} bytes")
            print(f"  Content Type: {file_data.get('content_type', 'unknown')}")
            print(f"  File Type: {file_data.get('file_type', 'unknown')}")


def show_file_upload_structure():
    """Show the structure of different file upload types."""
    print("\n=== FILE UPLOAD STRUCTURES ===")
    
    print("\n1. Multipart/Form-Data Structure:")
    print("""
    POST /upload HTTP/1.1
    Host: example.com
    Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Length: 1234

    ------WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="file"; filename="test.txt"
    Content-Type: text/plain

    This is the file content...
    ------WebKitFormBoundary7MA4YWxkTrZu0gW
    Content-Disposition: form-data; name="description"

    File description
    ------WebKitFormBoundary7MA4YWxkTrZu0gW--
    """)
    
    print("\n2. Raw Binary Upload Structure:")
    print("""
    POST /upload HTTP/1.1
    Host: example.com
    Content-Type: application/octet-stream
    Content-Length: 1024
    X-Filename: test.png

    [Binary file data here...]
    """)
    
    print("\n3. Base64 Encoded Upload Structure:")
    print("""
    POST /upload HTTP/1.1
    Host: example.com
    Content-Type: application/json

    {
        "filename": "test.txt",
        "data": "VGhpcyBpcyB0aGUgZmlsZSBjb250ZW50Li4u",
        "encoding": "base64"
    }
    """)


if __name__ == "__main__":
    show_file_upload_structure()
    demonstrate_file_interception()
    
    print("\n=== SUMMARY ===")
    print("File uploads in HTTP requests can be intercepted by:")
    print("1. Monitoring Content-Type headers for multipart/form-data")
    print("2. Parsing multipart boundaries to extract file parts")
    print("3. Analyzing Content-Disposition headers for filenames")
    print("4. Detecting file types using magic bytes")
    print("5. Capturing file metadata and content previews")
    print("\nThe R4U tracing system can be enhanced to:")
    print("- Automatically detect file uploads")
    print("- Extract file metadata and content")
    print("- Store file information in traces")
    print("- Provide file analysis capabilities")
