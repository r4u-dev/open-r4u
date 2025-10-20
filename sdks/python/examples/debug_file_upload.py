#!/usr/bin/env python3
"""
Debug version to understand why file upload detection isn't working.
"""

import io
import json
import requests
from r4u.tracing.http import trace_requests_session, PrintTracer


class DebugFileUploadTracer(PrintTracer):
    """Debug tracer to understand file upload detection."""
    
    def trace_request(self, request_info):
        """Debug tracing with detailed header analysis."""
        print("\n" + "="*80)
        print("🔍 DEBUG: Analyzing request")
        print("="*80)
        
        # Show all headers
        print("📋 Headers:")
        for key, value in request_info.headers.items():
            print(f"   {key}: {value}")
        
        # Check content-type specifically
        content_type = request_info.headers.get('content-type', '')
        print(f"\n📋 Content-Type: '{content_type}'")
        print(f"📋 Content-Type (lower): '{content_type.lower()}'")
        
        # Check for multipart
        is_multipart = 'multipart/form-data' in content_type.lower()
        print(f"🔍 Is multipart: {is_multipart}")
        
        # Check request payload
        payload_size = len(request_info.request_payload) if request_info.request_payload else 0
        print(f"📏 Payload size: {payload_size} bytes")
        
        if is_multipart and payload_size > 0:
            print("\n🎯 FILE UPLOAD DETECTED!")
            self._analyze_multipart_data(request_info.request_payload, content_type)
        else:
            print("\n❌ No file upload detected")
        
        # Call parent to show normal trace
        super().trace_request(request_info)
        print("="*80)
    
    def _analyze_multipart_data(self, payload, content_type):
        """Analyze multipart data."""
        try:
            # Extract boundary
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part.split('=', 1)[1].strip('"')
                    break
            
            if not boundary:
                print("❌ Could not extract boundary")
                return
            
            print(f"🔍 Boundary: '{boundary}'")
            
            # Split by boundary
            boundary_bytes = f'--{boundary}'.encode()
            parts = payload.split(boundary_bytes)
            
            print(f"📦 Found {len(parts)} parts")
            
            for i, part in enumerate(parts):
                if part.strip():
                    print(f"\n📄 Part {i}:")
                    print(f"   Size: {len(part)} bytes")
                    
                    # Look for headers
                    if b'\r\n\r\n' in part:
                        headers_raw, body = part.split(b'\r\n\r\n', 1)
                        print(f"   Headers: {headers_raw.decode('utf-8', errors='ignore')[:100]}...")
                        print(f"   Body size: {len(body)} bytes")
                        
                        # Check for filename
                        if b'filename=' in headers_raw:
                            print("   ✅ Contains filename!")
                        else:
                            print("   ❌ No filename found")
                    
        except Exception as e:
            print(f"❌ Error analyzing multipart: {e}")


def test_file_upload():
    """Test file upload with debug tracing."""
    print("🚀 Debug File Upload Test")
    print("=" * 50)
    
    # Create session with debug tracing
    session = requests.Session()
    trace_requests_session(session, DebugFileUploadTracer())
    
    # Create test file
    test_content = "This is a test file content.\nWith multiple lines."
    
    print("\n📤 Uploading file...")
    
    # Upload file
    files = {
        'file': ('test.txt', io.BytesIO(test_content.encode()), 'text/plain')
    }
    data = {'description': 'Test upload'}
    
    try:
        response = session.post('https://httpbin.org/post', files=files, data=data)
        print(f"\n✅ Response status: {response.status_code}")
    except Exception as e:
        print(f"\n❌ Request failed: {e}")


if __name__ == "__main__":
    test_file_upload()
