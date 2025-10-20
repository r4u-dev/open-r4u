# HTTP File Upload Interception Guide

This document explains how HTTP file uploads work and how to intercept and analyze file data in HTTP requests using the R4U tracing system.

## Table of Contents

1. [How HTTP File Uploads Work](#how-http-file-uploads-work)
2. [File Upload Formats](#file-upload-formats)
3. [Intercepting File Data](#intercepting-file-data)
4. [R4U Integration](#r4u-integration)
5. [Examples](#examples)
6. [Best Practices](#best-practices)

## How HTTP File Uploads Work

HTTP file uploads typically use the `POST` method with special content types to send file data from client to server. The most common approaches are:

### 1. Multipart/Form-Data (Most Common)

Files are embedded within form data using the `multipart/form-data` content type:

```
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
```

### 2. Raw Binary Upload

Files are sent as raw binary data:

```
POST /upload HTTP/1.1
Host: example.com
Content-Type: application/octet-stream
Content-Length: 1024
X-Filename: test.png

[Binary file data here...]
```

### 3. Base64 Encoded Upload

Files are encoded as base64 strings in JSON:

```
POST /upload HTTP/1.1
Host: example.com
Content-Type: application/json

{
    "filename": "test.txt",
    "data": "VGhpcyBpcyB0aGUgZmlsZSBjb250ZW50Li4u",
    "encoding": "base64"
}
```

## File Upload Formats

### Multipart/Form-Data Structure

- **Boundary**: Unique string that separates different parts
- **Headers**: Each part has headers like `Content-Disposition` and `Content-Type`
- **Body**: The actual file content or form field value

Key headers in multipart data:
- `Content-Disposition: form-data; name="field_name"; filename="file.txt"`
- `Content-Type: text/plain` (or appropriate MIME type)

### Binary Data Structure

- **Content-Type**: Usually `application/octet-stream` or specific MIME type
- **Content-Length**: Size of the binary data
- **Optional Headers**: `X-Filename`, `Content-Disposition` for metadata

## Intercepting File Data

To intercept file uploads in HTTP requests, you need to:

1. **Monitor Content-Type Headers**: Look for `multipart/form-data` or binary content types
2. **Parse Multipart Boundaries**: Extract the boundary string and split the payload
3. **Extract File Metadata**: Parse `Content-Disposition` headers for filenames and field names
4. **Analyze File Content**: Detect file types using magic bytes, extract content previews
5. **Handle Binary Data**: Safely process binary content without corruption

### Key Detection Methods

```python
def is_file_upload(request_info):
    """Detect if request contains file uploads."""
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
```

### File Type Detection

Use magic bytes (file signatures) to detect file types:

```python
def detect_file_type(content: bytes) -> str:
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
        if content.startswith(signature):
            return file_type
    
    return "unknown"
```

## R4U Integration

The R4U tracing system can be enhanced to automatically detect and analyze file uploads:

### Enhanced Tracer

```python
class EnhancedFileTracer(UniversalTracer):
    """Enhanced tracer that captures file upload information."""
    
    def trace_request(self, request_info: RawRequestInfo) -> None:
        # Check for file uploads
        if self._is_file_upload(request_info):
            file_data = self._extract_file_data(request_info)
            # Store file information in trace metadata
        
        super().trace_request(request_info)
```

### File Data Extraction

```python
def _extract_file_data(self, request_info: RawRequestInfo) -> Dict[str, Any]:
    """Extract file data from request."""
    content_type = request_info.headers.get('content-type', '')
    
    if 'multipart/form-data' in content_type:
        return self._extract_multipart_files(request_info)
    else:
        return self._extract_binary_file(request_info)
```

### Metadata Storage

File information can be stored in the trace metadata:

```python
file_metadata = {
    'upload_type': 'multipart',
    'files': [
        {
            'filename': 'test.txt',
            'field_name': 'file',
            'content_type': 'text/plain',
            'size': 1024,
            'file_type': 'text',
            'is_binary': False,
            'content_preview': 'File content preview...'
        }
    ],
    'total_files': 1,
    'total_size': 1024
}
```

## Examples

### Basic File Upload Detection

```python
from r4u.tracing.http import trace_requests_session

# Create session with file upload tracing
session = requests.Session()
trace_requests_session(session, FileUploadTracer())

# Upload a file
files = {'file': ('test.txt', open('test.txt', 'rb'), 'text/plain')}
response = session.post('https://api.example.com/upload', files=files)
```

### Advanced File Analysis

```python
class FileUploadInterceptor:
    """Interceptor for capturing and analyzing file uploads."""
    
    def __init__(self, r4u_client: R4UClient):
        self.r4u_client = r4u_client
        self.captured_files = []
    
    def setup_tracing(self, session: requests.Session):
        tracer = EnhancedFileTracer(self.r4u_client, "http_requests")
        trace_requests_session(session, tracer)
```

### Multipart Data Parsing

```python
def parse_multipart_data(payload: bytes, boundary: str) -> List[Dict]:
    """Parse multipart form data to extract file information."""
    boundary_bytes = f'--{boundary}'.encode()
    parts = payload.split(boundary_bytes)
    
    files = []
    for part in parts[1:-1]:  # Skip first and last empty parts
        if part.strip():
            file_info = parse_multipart_part(part)
            if file_info:
                files.append(file_info)
    
    return files
```

## Best Practices

### 1. Content Type Detection

Always check the `Content-Type` header first to determine the upload format:

```python
content_type = request_info.headers.get('content-type', '').lower()
if 'multipart/form-data' in content_type:
    # Handle multipart upload
elif 'application/octet-stream' in content_type:
    # Handle binary upload
```

### 2. Safe Binary Handling

When processing binary data:

- Use `errors='ignore'` when decoding text
- Check for null bytes to detect binary content
- Use magic bytes for file type detection
- Limit content previews to avoid memory issues

### 3. Memory Management

For large files:

- Stream processing instead of loading entire file into memory
- Limit preview sizes (e.g., first 200 bytes)
- Use base64 encoding for storage in JSON traces

### 4. Error Handling

Always handle parsing errors gracefully:

```python
try:
    file_info = parse_multipart_part(part)
except Exception as e:
    print(f"Error parsing part: {e}")
    continue
```

### 5. Security Considerations

- Validate file types and sizes
- Be cautious with executable file types
- Sanitize filenames and content previews
- Consider privacy implications of storing file content

## Implementation Files

The following example files demonstrate file upload interception:

1. **`examples/file_upload_example.py`**: Basic file upload detection and analysis
2. **`examples/enhanced_file_tracing.py`**: Advanced R4U integration with file tracing
3. **`examples/practical_file_interception.py`**: Real-world file upload interception

## Summary

HTTP file uploads can be intercepted by:

1. **Monitoring Content-Type headers** for multipart/form-data or binary indicators
2. **Parsing multipart boundaries** to extract individual file parts
3. **Analyzing Content-Disposition headers** for filenames and field names
4. **Detecting file types** using magic bytes and content analysis
5. **Capturing file metadata** and content previews for tracing

The R4U tracing system can be enhanced to automatically detect, analyze, and store file upload information, providing comprehensive visibility into file transfer operations.
