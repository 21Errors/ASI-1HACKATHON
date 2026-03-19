#!/usr/bin/env python3
"""
Complete startup and testing script
Runs test_startup.py, starts server, tests endpoints, keeps server running
"""

import subprocess
import sys
import os
import time
import socket

def wait_for_server(host='localhost', port=8000, timeout=30):
    """Wait for server to be ready"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def main():
    os.chdir('C:\\users\\kamog\\asihackathon')
    
    # Step 1: Run startup test
    print("\n" + "="*70)
    print("STEP 1: Running startup verification test")
    print("="*70)
    
    result = subprocess.run([sys.executable, 'test_startup.py'])
    
    if result.returncode != 0:
        print("\n" + "!"*70)
        print("❌ STARTUP TEST FAILED")
        print("!"*70)
        return False
    
    print("\n" + "✓"*70)
    print("✅ STARTUP TEST PASSED - Starting server...")
    print("✓"*70)
    
    # Step 2: Start server
    print("\nSTEP 2: Starting uvicorn server on http://0.0.0.0:8000")
    print("="*70)
    
    server = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    print(f"Server PID: {server.pid}")
    print("Waiting for server to initialize...")
    
    # Monitor startup output
    startup_lines = []
    import threading
    def read_output():
        for line in server.stdout:
            startup_lines.append(line.strip())
            print(f"  [SERVER] {line.rstrip()}")
            if "Uvicorn running" in line or "Application startup complete" in line:
                break
    
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    
    # Wait for server to be ready
    time.sleep(3)
    if not wait_for_server():
        print("\n❌ Server failed to start on port 8000")
        server.terminate()
        return False
    
    print("\n✅ Server is running!")
    
    # Step 3: Test endpoints
    print("\nSTEP 3: Testing endpoints")
    print("="*70)
    
    try:
        import requests
        
        tests = [
            ("GET", "http://localhost:8000/api/health"),
            ("GET", "http://localhost:8000/api/industries"),
            ("POST", "http://localhost:8000/api/test-finder", {}),
        ]
        
        for idx, test in enumerate(tests, 1):
            method, url = test[0], test[1]
            data = test[2] if len(test) > 2 else None
            
            print(f"\n[{idx}] {method} {url}")
            try:
                if method == "GET":
                    resp = requests.get(url, timeout=5)
                else:
                    resp = requests.post(url, json=data, timeout=5)
                
                print(f"    Status: {resp.status_code}")
                try:
                    body = resp.json()
                    import json
                    print(f"    Response: {json.dumps(body, indent=6)[:300]}...")
                except:
                    print(f"    Response: {resp.text[:200]}...")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    except ImportError:
        print("requests library not installed, using curl instead...")
        os.system('curl -s http://localhost:8000/api/health')
    
    # Final summary
    print("\n" + "="*70)
    print("✅ SERVER IS RUNNING - DO NOT CLOSE THIS WINDOW")
    print("="*70)
    print(f"Server PID: {server.pid}")
    print("API Base URL: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("\nTo stop the server:")
    print(f"  Windows: taskkill /PID {server.pid} /F")
    print(f"  Or: Stop-Process -Id {server.pid}")
    print("="*70 + "\n")
    
    # Keep server running
    try:
        server.wait()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.terminate()
        server.wait()
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
