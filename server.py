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

sessions = {}
class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        self.CHATCONN = sqlite3.connect('chatroom-database.db', check_same_thread=False)
        self.CHAT = self.CHATCONN.cursor()
        self.LOGINCONN = sqlite3.connect('login-database.db', check_same_thread=False)
        self.LOGIN = self.LOGINCONN.cursor()
        self.PDCONN = sqlite3.connect('player-data-database.db', check_same_thread=False)
        self.PD = self.PDCONN.cursor()

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
            self.upload_message(sessions[data['session']], data['text'])
            self.send_json_response(200, {'success': True})
        elif self.path == '/get_messages':
            self.get_messages()
        elif self.path == '/login':
            data = json.loads(post_data)
            self.login(data['username'], data['password'])

    def upload_message(self, username, text):
        self.CHAT.execute('INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)', (username, text, int(time.time())))
        self.CHATCONN.commit()
        # Broadcast the message to WebSocket clients
        asyncio.run(broadcast_message({'username': username, 'message': text, 'timestamp': int(time.time())}))

    def get_messages(self):
        self.CHAT.execute('SELECT * FROM messages ORDER BY timestamp')
        messages = self.CHAT.fetchall()
        messages = [{'username': x[1], 'message': x[2], 'timestamp': x[3]} for x in messages]
        self.send_json_response(200, {'messages': messages})

    def login(self, username, password):
        random.seed(password + username)
        password = int(str(random.random())[2:])
        # Check if username already exists
        self.LOGIN.execute('SELECT * FROM login WHERE username = ?', (username,))
        if self.LOGIN.fetchone() is not None:
            # check if password is correct
            self.LOGIN.execute('SELECT * FROM login WHERE username = ? AND password = ?', (username, password))
            if self.LOGIN.fetchone() is None:
                self.send_json_response(400, {'error': 'Incorrect password'})
                return 
            else: # login successful
                random.seed(time.time())
                sessionID = int(str(random.random())[2:])
                sessions[str(sessionID)] = username
                print(sessionID)
                self.send_json_response(200, {'success': True, "session": sessionID})
                return 
        else:
            self.LOGIN.execute('INSERT INTO login (username, password) VALUES (?, ?)', (username, password))
            self.LOGINCONN.commit()
            # create a new row in the player_data table
            self.PD.execute('INSERT INTO basicPlayerData (username) VALUES (?)', (username,))
            self.PDCONN.commit()
            random.seed(time.time())
            sessionID = int(str(random.random())[2:])
            sessions[str(sessionID)] = username
            self.send_json_response(200, {'success': True, "session": sessionID})
        return True

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

# WebSocket connection handler
connected_clients = []

async def websocket_handler(websocket, path):
    connected_clients.append(websocket)
    try:
        async for message in websocket:
            pass  # WebSocket clients do not send messages in this example
    finally:
        connected_clients.remove(websocket)

async def broadcast_message(message):
    for ws in connected_clients:
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