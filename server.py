import RangeHTTPServer
import socketserver
import os
import time
import random
import json

PORT = 8026

print("starting server")

class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

# Create the server
server = socketserver.TCPServer(('', PORT), CustomRequestHandler)

print(f"Server started on port {PORT}")

# Start the server
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("Shutting down server")
    server.shutdown()
    server.server_close()
