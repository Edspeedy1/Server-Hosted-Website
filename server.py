import RangeHTTPServer
import socketserver
import os
import time
import threading
import random
import json
import sqlite3
import asyncio
import websockets

HTTP_PORT = int(os.getenv('PORT', 8026))
WEBSOCKET_PORT = 8765

print("starting server")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        self.CONN = sqlite3.connect('chatroom-database.db', check_same_thread=False)
        self.C = self.CONN.cursor()
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
        super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        if self.path == '/upload_message':
            data = json.loads(post_data)
            self.upload_message(data['username'], data['text'], data['roomid'])
            self.send_json_response(200, {'success': True})
        elif self.path == '/get_messages':
            roomid = self.headers['roomid']
            self.get_messages(roomid)

    def upload_message(self, username, text, roomid):
        self.C.execute('INSERT INTO messages (username, message, room_name, timestamp) VALUES (?, ?, ?, ?)', (username, text, roomid, int(time.time())))
        self.CONN.commit()
        # Broadcast the message to WebSocket clients
        asyncio.run(broadcast_message(roomid, {'username': username, 'message': text, 'timestamp': int(time.time())}))

    def get_messages(self, roomid):
        self.C.execute('SELECT * FROM messages WHERE room_name = ? ORDER BY timestamp', (roomid,))
        messages = self.C.fetchall()
        messages = [{'username': x[2], 'message': x[3], 'timestamp': x[4]} for x in messages]
        self.send_json_response(200, {'messages': messages})

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

# WebSocket connection handler
connected_clients = {}

async def websocket_handler(websocket, path):
    room_id = path.strip("/")
    if room_id not in connected_clients:
        connected_clients[room_id] = []
    connected_clients[room_id].append(websocket)
    try:
        async for message in websocket:
            pass  # WebSocket clients do not send messages in this example
    finally:
        connected_clients[room_id].remove(websocket)

async def broadcast_message(room_id, message):
    if room_id in connected_clients:
        for ws in connected_clients[room_id]:
            await ws.send(json.dumps(message))

# Starting the WebSocket server
def start_websocket_server():
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)     # Set the event loop for this thread
    server = websockets.serve(websocket_handler, "0.0.0.0", WEBSOCKET_PORT)
    loop.run_until_complete(server)  # Start the WebSocket server
    loop.run_forever()

with ThreadedHTTPServer(("", HTTP_PORT), CustomRequestHandler) as httpd:
    print(f"HTTP server serving at port {HTTP_PORT}")
    
    # Start WebSocket server in a separate thread
    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.daemon = True
    websocket_thread.start()

    # Start the HTTP server
    httpd.serve_forever()
