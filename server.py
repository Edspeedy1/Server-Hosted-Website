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
import hashlib

HTTP_PORT = int(os.getenv('PORT', 8026))
WEBSOCKET_PORT = 8765

print("starting server")

class ConnectedClient:
    def __init__(self, username, sessionID):
        self.username = username
        self.sessionID = sessionID
        self.lastActiveTime = time.time()

    def update_last_active_time(self):
        self.lastActiveTime = time.time()

class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.chat_conn = sqlite3.connect('chatroom-database.db', check_same_thread=False)
        self.chat_cursor = self.chat_conn.cursor()
        self.login_conn = sqlite3.connect('login-database.db', check_same_thread=False)
        self.login_cursor = self.login_conn.cursor()
        self.player_data_conn = sqlite3.connect('player-data-database.db', check_same_thread=False)
        self.player_data_cursor = self.player_data_conn.cursor()

    def close(self):
        self.chat_conn.close()
        self.login_conn.close()
        self.player_data_conn.close()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

sessions = {}
class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        self.db = DatabaseManager()  # Use shared database manager
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
            if len(data['text']) > 1000:
                self.send_json_response(400, {'error': 'Message too long'})
                return
            sessions[data['session']].update_last_active_time()
            self.upload_message(sessions[data['session']].username, data['text'])
            self.send_json_response(200, {'success': True})
        elif self.path == '/get_messages':
            self.get_messages()
        elif self.path == '/login':
            data = json.loads(post_data)
            self.login(data['username'], data['password'])

    def upload_message(self, username, text):
        self.db.chat_cursor.execute('INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)', (username, text, int(time.time())))
        self.db.chat_conn.commit()
        # Broadcast the message to WebSocket clients
        asyncio.run(broadcast_message({'username': username, 'message': text, 'timestamp': int(time.time()), 'type': 'chat'}))

    def get_messages(self):
        self.db.chat_cursor.execute('SELECT * FROM messages ORDER BY timestamp')
        messages = self.db.chat_cursor.fetchall()
        messages = [{'username': x[1], 'message': x[2], 'timestamp': x[3]} for x in messages]
        self.send_json_response(200, {'messages': messages})

    def login(self, username, password):
        password = hashlib.sha256((password + username).encode('utf-8')).hexdigest()
        # Check if username already exists
        self.db.login_cursor.execute('SELECT * FROM login WHERE username = ?', (username,))
        if self.db.login_cursor.fetchone() is not None:
            # check if password is correct
            self.db.login_cursor.execute('SELECT * FROM login WHERE username = ? AND password = ?', (username, password))
            if self.db.login_cursor.fetchone() is None:
                self.send_json_response(400, {'error': 'Incorrect password'})
                return 
            else: # login successful
                sessionID = hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()
                sessions[str(sessionID)] = ConnectedClient(username, sessionID)
                self.send_json_response(200, {'success': True, "session": sessionID})
                return 
        else:
            self.db.login_cursor.execute('INSERT INTO login (username, password) VALUES (?, ?)', (username, password))
            self.db.login_conn.commit()
            # create a new row in the player_data table
            self.db.player_data_cursor.execute('INSERT INTO basicPlayerData (username) VALUES (?)', (username,))
            self.db.player_data_conn.commit()
            random.seed(time.time())
            sessionID = hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()
            sessions[str(sessionID)] = ConnectedClient(username, sessionID)
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

def start_inactivity_check(timeout):
    db = DatabaseManager()
    while True:
        for _ in range(100):
            print("Checking inactive sessions...")
            current_time = time.time()
            inactive_sessions = [session_id for session_id, client in sessions.items() if current_time - client.lastActiveTime > timeout]
            
            for session_id in inactive_sessions:
                print(f"Session {session_id} is inactive for too long. Removing user.")
                asyncio.run(broadcast_message({"type": "remove_user", "session": session_id, "username": sessions[session_id].username}))
                del sessions[session_id]
            
            time.sleep(60)
        
        active_sessions = tuple(map(lambda x: x.username, list(sessions.values())))
        placeholders = ', '.join('?' for _ in active_sessions)

        db.login_cursor.execute(f'DELETE FROM login WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        db.login_conn.commit()
        db.player_data_cursor.execute(f'DELETE FROM basicPlayerData WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        db.player_data_conn.commit()

        

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
    
    # Start inactivity check in a separate thread
    inactivity_thread = threading.Thread(target=start_inactivity_check, args=(3600,))
    inactivity_thread.daemon = True
    inactivity_thread.start()

    # Start the HTTP server
    httpd.serve_forever()
