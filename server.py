import http.server
import socketserver
import os
import time
import threading
import random
import json

PORT = 8026

print("starting server")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class CustomRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
        super().end_headers()

    def send_file(self, status_code, content):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        self.wfile.write(content.encode())

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'

        # Set the response status code
        self.send_response(200)
        # Set the content type of the response
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Write the response body
        try:
            with open(self.path[1:], 'r') as f:
                self.wfile.write(f.read().encode('utf-8'))
        except Exception as e:
            print(e)
            self.send_file(500, 'Error: ' + str(e))

with ThreadedHTTPServer(("", PORT), CustomRequestHandler) as httpd:
    print("serving at port", PORT)
    # Start a new thread for serving requests
    for i in range(10):
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True  # Daemonize the thread so it exits when the main thread exits
        server_thread.start()
        # Wait for the server thread to finish (if ever)
        server_thread.join()