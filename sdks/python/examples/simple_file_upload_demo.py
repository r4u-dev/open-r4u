#!/usr/bin/env python3
"""
Simple demonstration of HTTP file upload interception.

This example shows how to detect and analyze file uploads in HTTP requests
using the current R4U tracing system.
"""

import io
import json
import requests
from r4u.tracing.http import trace_requests_session


class FileUploadTracer:
    """Enhanced tracer that detects and analyzes file uploads."""
    
    def trace_request(self, request_info):
        """Enhanced tracing with file upload detection."""
        # Basic trace information
        print("--------------------------------")
        print(f"Request: {request_info.method} {request_info.url}")
        print(f"Status: {request_info.status_code}")
        print(f"Duration: {request_info.duration_ms:.2f}ms")
        
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


def demonstrate_file_upload_interception():
    """Demonstrate file upload interception."""
    print("HTTP File Upload Interception Demo")
    print("=" * 50)
    
    # Create a session with file upload tracing
    session = requests.Session()
    trace_requests_session(session, FileUploadTracer())
    
    # Create test files
    test_files = {
        'text.txt': "This is a test text file.\nIt contains multiple lines of text.",
        'data.json': json.dumps({"message": "Hello from JSON file", "data": [1, 2, 3]}, indent=2),
        'binary.png': b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    }
    
    print("\n1. Testing single file upload...")
    
    # Test single file upload
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
    demonstrate_file_upload_interception()
    
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
