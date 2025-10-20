#!/usr/bin/env python3
"""
Example demonstrating HTTP file uploads and how to intercept file data.

This example shows:
1. Different ways files are uploaded via HTTP (multipart/form-data, raw binary, etc.)
2. How the current R4U tracing system captures file data
3. How to enhance tracing to better handle file uploads
"""

import io
import json
import tempfile
import requests
from pathlib import Path
from r4u.tracing.http import trace_requests_session, PrintTracer


class FileUploadTracer(PrintTracer):
    """Enhanced tracer that specifically handles file upload detection and analysis."""
    
    def trace_request(self, request_info):
        """Enhanced tracing with file upload detection."""
        super().trace_request(request_info)
        
        # Check if this is a file upload request
        if self._is_file_upload(request_info):
            self._analyze_file_upload(request_info)
    
    def _is_file_upload(self, request_info):
        """Detect if this request contains file uploads."""
        content_type = request_info.headers.get('content-type', '').lower()
        
        # Check for multipart/form-data (most common file upload format)
        if 'multipart/form-data' in content_type:
            return True
        
        # Check for other file-related content types
        file_content_types = [
            'application/octet-stream',
            'image/',
            'video/',
            'audio/',
            'text/plain',
            'application/pdf',
            'application/zip'
        ]
        
        return any(ct in content_type for ct in file_content_types)
    
    def _analyze_file_upload(self, request_info):
        """Analyze file upload data and extract useful information."""
        print("\n=== FILE UPLOAD DETECTED ===")
        print(f"Content-Type: {request_info.headers.get('content-type', 'unknown')}")
        print(f"Request Size: {request_info.request_size or len(request_info.request_payload or b'')} bytes")
        
        if request_info.request_payload:
            self._extract_file_info(request_info.request_payload, request_info.headers)
    
    def _extract_file_info(self, payload, headers):
        """Extract file information from the payload."""
        content_type = headers.get('content-type', '')
        
        if 'multipart/form-data' in content_type:
            self._parse_multipart_data(payload, content_type)
        else:
            self._analyze_binary_data(payload, content_type)
    
    def _parse_multipart_data(self, payload, content_type):
        """Parse multipart/form-data to extract file information."""
        try:
            # Extract boundary from content-type header
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part.split('=', 1)[1].strip('"')
                    break
            
            if not boundary:
                print("Could not extract boundary from multipart data")
                return
            
            # Split payload by boundary
            boundary_bytes = f'--{boundary}'.encode()
            parts = payload.split(boundary_bytes)
            
            print(f"Found {len(parts) - 2} parts in multipart data")  # -2 for start/end markers
            
            for i, part in enumerate(parts[1:-1]):  # Skip first and last empty parts
                if part.strip():
                    self._parse_multipart_part(part, i)
                    
        except Exception as e:
            print(f"Error parsing multipart data: {e}")
    
    def _parse_multipart_part(self, part, part_index):
        """Parse a single part of multipart data."""
        try:
            # Split headers and body
            if b'\r\n\r\n' in part:
                headers_raw, body = part.split(b'\r\n\r\n', 1)
            elif b'\n\n' in part:
                headers_raw, body = part.split(b'\n\n', 1)
            else:
                print(f"Part {part_index}: Could not separate headers from body")
                return
            
            # Parse headers
            headers = {}
            for line in headers_raw.decode('utf-8', errors='ignore').split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            print(f"\nPart {part_index}:")
            print(f"  Headers: {headers}")
            
            # Extract filename and field name from Content-Disposition
            content_disposition = headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                # Extract filename
                filename_start = content_disposition.find('filename=') + 9
                filename_end = content_disposition.find(';', filename_start)
                if filename_end == -1:
                    filename_end = len(content_disposition)
                filename = content_disposition[filename_start:filename_end].strip('"')
                print(f"  Filename: {filename}")
            
            if 'name=' in content_disposition:
                # Extract field name
                name_start = content_disposition.find('name=') + 5
                name_end = content_disposition.find(';', name_start)
                if name_end == -1:
                    name_end = len(content_disposition)
                field_name = content_disposition[name_start:name_end].strip('"')
                print(f"  Field name: {field_name}")
            
            # Analyze body content
            content_type = headers.get('content-type', 'unknown')
            print(f"  Content-Type: {content_type}")
            print(f"  Body size: {len(body)} bytes")
            
            # Show preview of text content
            if content_type.startswith('text/') or 'json' in content_type:
                try:
                    preview = body[:200].decode('utf-8', errors='ignore')
                    print(f"  Content preview: {preview}...")
                except Exception:
                    pass
            
        except Exception as e:
            print(f"Error parsing part {part_index}: {e}")
    
    def _analyze_binary_data(self, payload, content_type):
        """Analyze binary file data."""
        print("Binary file detected")
        print(f"Size: {len(payload)} bytes")
        print(f"Content-Type: {content_type}")
        
        # Try to detect file type from magic bytes
        if len(payload) >= 4:
            magic_bytes = payload[:4]
            file_type = self._detect_file_type(magic_bytes)
            if file_type:
                print(f"Detected file type: {file_type}")
        
        # Show hex preview
        hex_preview = ' '.join(f'{b:02x}' for b in payload[:16])
        print(f"Hex preview: {hex_preview}...")
    
    def _detect_file_type(self, magic_bytes):
        """Detect file type from magic bytes."""
        magic_signatures = {
            b'\x89PNG': 'PNG image',
            b'\xff\xd8\xff': 'JPEG image',
            b'GIF8': 'GIF image',
            b'%PDF': 'PDF document',
            b'PK\x03\x04': 'ZIP archive',
            b'\x1f\x8b\x08': 'GZIP archive',
        }
        
        for signature, file_type in magic_signatures.items():
            if magic_bytes.startswith(signature):
                return file_type
        
        return None


def create_test_files():
    """Create test files for upload examples."""
    test_files = {}
    
    # Create a text file
    text_content = "This is a test file for HTTP upload demonstration.\nIt contains multiple lines of text."
    test_files['text.txt'] = text_content.encode('utf-8')
    
    # Create a JSON file
    json_content = {"message": "Hello from JSON file", "timestamp": "2024-01-01T00:00:00Z", "data": [1, 2, 3]}
    test_files['data.json'] = json.dumps(json_content, indent=2).encode('utf-8')
    
    # Create a binary file (simulated)
    binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    test_files['image.png'] = binary_content
    
    return test_files


def example_multipart_file_upload():
    """Example of multipart/form-data file upload."""
    print("=== MULTIPART FILE UPLOAD EXAMPLE ===")
    
    # Create test files
    test_files = create_test_files()
    
    # Create a session with file upload tracing
    session = requests.Session()
    trace_requests_session(session, FileUploadTracer())
    
    # Create temporary files
    temp_files = {}
    for filename, content in test_files.items():
        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix=f'_{filename}', delete=False)
        temp_file.write(content)
        temp_file.close()
        temp_files[filename] = temp_file.name
    
    try:
        # Example 1: Single file upload
        print("\n1. Single file upload:")
        with open(temp_files['text.txt'], 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            
            # This would normally go to a real endpoint
            # response = session.post('https://httpbin.org/post', files=files, data={'description': 'Test file upload'})
            print("Would upload file with multipart/form-data")
        
        # Example 2: Multiple files upload
        print("\n2. Multiple files upload:")
        files = []
        for filename, temp_path in temp_files.items():
            files.append(('files', (filename, open(temp_path, 'rb'), 'application/octet-stream')))
        
        print("Would upload multiple files with multipart/form-data")
        
        # Close file handles
        for _, (_, file_handle, _) in files:
            file_handle.close()
        
        # Example 3: Raw binary upload
        print("\n3. Raw binary upload:")
        print("Would upload raw binary data")
        
    finally:
        # Clean up temporary files
        for temp_path in temp_files.values():
            Path(temp_path).unlink(missing_ok=True)


def example_file_upload_interception():
    """Example showing how to intercept and analyze file uploads."""
    print("\n=== FILE UPLOAD INTERCEPTION EXAMPLE ===")
    
    # Create a custom tracer that captures file data
    class FileCaptureTracer(FileUploadTracer):
        def __init__(self):
            super().__init__()
            self.captured_files = []
        
        def _analyze_file_upload(self, request_info):
            super()._analyze_file_upload(request_info)
            
            # Store file information for later analysis
            file_info = {
                'url': request_info.url,
                'method': request_info.method,
                'content_type': request_info.headers.get('content-type'),
                'size': request_info.request_size or len(request_info.request_payload or b''),
                'timestamp': request_info.started_at,
                'payload': request_info.request_payload
            }
            self.captured_files.append(file_info)
    
    # Create session with file capture tracer
    session = requests.Session()
    tracer = FileCaptureTracer()
    trace_requests_session(session, tracer)
    
    # Simulate file uploads (using httpbin.org for testing)
    test_files = create_test_files()
    
    try:
        # Upload a text file
        print("\nUploading text file...")
        files = {'file': ('test.txt', io.BytesIO(test_files['text.txt']), 'text/plain')}
        response = session.post('https://httpbin.org/post', files=files)
        print(f"Response status: {response.status_code}")
        
        # Upload a JSON file
        print("\nUploading JSON file...")
        files = {'file': ('data.json', io.BytesIO(test_files['data.json']), 'application/json')}
        response = session.post('https://httpbin.org/post', files=files)
        print(f"Response status: {response.status_code}")
        
        # Upload binary data
        print("\nUploading binary data...")
        files = {'file': ('image.png', io.BytesIO(test_files['image.png']), 'image/png')}
        response = session.post('https://httpbin.org/post', files=files)
        print(f"Response status: {response.status_code}")
        
        # Show captured file information
        print(f"\n=== CAPTURED {len(tracer.captured_files)} FILE UPLOADS ===")
        for i, file_info in enumerate(tracer.captured_files):
            print(f"\nFile {i+1}:")
            print(f"  URL: {file_info['url']}")
            print(f"  Method: {file_info['method']}")
            print(f"  Content-Type: {file_info['content_type']}")
            print(f"  Size: {file_info['size']} bytes")
            print(f"  Timestamp: {file_info['timestamp']}")
            
    except Exception as e:
        print(f"Error during file upload testing: {e}")


def demonstrate_file_data_structure():
    """Demonstrate the structure of file data in HTTP requests."""
    print("\n=== FILE DATA STRUCTURE DEMONSTRATION ===")
    
    # Show how multipart/form-data looks
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
    
    # Show how raw binary upload looks
    print("\n2. Raw Binary Upload Structure:")
    print("""
    POST /upload HTTP/1.1
    Host: example.com
    Content-Type: application/octet-stream
    Content-Length: 1024

    [Binary file data here...]
    """)
    
    # Show how base64 encoded upload looks
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


def main():
    """Main function demonstrating file upload interception."""
    print("HTTP File Upload Interception Demo")
    print("=" * 50)
    
    # Show file data structure
    demonstrate_file_data_structure()
    
    # Demonstrate multipart file upload
    example_multipart_file_upload()
    
    # Demonstrate file upload interception
    example_file_upload_interception()
    
    print("\n=== SUMMARY ===")
    print("File uploads in HTTP requests typically use:")
    print("1. multipart/form-data for form-based uploads")
    print("2. application/octet-stream for raw binary uploads")
    print("3. application/json with base64 encoding for API uploads")
    print("\nTo intercept file data:")
    print("1. Monitor Content-Type headers")
    print("2. Parse multipart boundaries for form uploads")
    print("3. Extract file metadata from Content-Disposition headers")
    print("4. Analyze payload size and content")
    print("5. Use magic bytes to detect file types")


if __name__ == "__main__":
    main()
