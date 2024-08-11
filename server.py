import RangeHTTPServer
import socketserver
import os
import time
import threading
import random
import json
import sqlite3
import hashlib

# logging for debug messages on server console
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HTTP_PORT = int(os.getenv('PORT', 8026))

print("starting server")

# class for keeping track of active sessions
class ConnectedClient:
    def __init__(self, username, sessionID):
        self.username = username
        self.sessionID = sessionID
        self.lastActiveTime = time.time()
    
    def __str__(self):
        return f"username: {self.username}, sessionID: {self.sessionID}, lastActiveTime: {self.lastActiveTime}"

    def update_last_active_time(self):
        self.lastActiveTime = time.time()

# singleton database manager to help with the inactivity check thread
class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.chat_conn = sqlite3.connect('saveData/chatroom-database.db', check_same_thread=False)
        self.chat_cursor = self.chat_conn.cursor()
        self.login_conn = sqlite3.connect('saveData/login-database.db', check_same_thread=False)
        self.login_cursor = self.login_conn.cursor()
        self.player_data_conn = sqlite3.connect('saveData/player-data-database.db', check_same_thread=False)
        self.player_data_cursor = self.player_data_conn.cursor()

    def close(self):
        self.chat_conn.close()
        self.login_conn.close()
        self.player_data_conn.close()

# legacy code, was necessary but IDK anymore and i'm too scared to touch it
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


# dictionary of active sessions
sessions = {}

# the meat and potatoes of the server
class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        self.db = DatabaseManager()  # Use shared database manager
        super().__init__(request, client_address, server)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')  # Add CORS header
        super().end_headers()

    def send_file(self, status_code, content): # unused
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
            logger.info(data)
            logger.info(sessions)
            if len(data['text']) > 1000:
                self.send_json_response(400, {'error': 'Message too long'})
                return
            try:
                sessions[data['session']].update_last_active_time()
                self.upload_message(sessions[data['session']].username, data['text'])
                self.send_json_response(200, {'success': True})
            except KeyError as e:
                logger.error(e)
                logger.info(data["session"])
                self.send_json_response(200, {'error': 'Invalid session'})

        elif self.path == '/get_messages':
            self.get_messages()

        elif self.path == '/login':
            data = json.loads(post_data)
            self.login(data['username'], data['password'])

    def upload_message(self, username, text):
        self.db.chat_cursor.execute('INSERT INTO messages (username, message, timestamp) VALUES (?, ?, ?)', (username, text, int(time.time())))
        self.db.chat_conn.commit()

    def get_messages(self):
        self.db.chat_cursor.execute('SELECT * FROM messages ORDER BY timestamp DESC LIMIT 50')
        messages = self.db.chat_cursor.fetchall()[::-1]
        messages = [{'username': x[1], 'message': x[2], 'timestamp': x[3]} for x in messages]
        self.send_json_response(200, {'messages': messages})

    def login(self, username, password):
        logger.info("Logging in as " + username)
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
        else: # new account creation
            self.db.login_cursor.execute('INSERT INTO login (username, password) VALUES (?, ?)', (username, password))
            self.db.login_conn.commit()
            # create a new row in the player_data table
            self.db.player_data_cursor.execute('INSERT INTO basicPlayerData (username) VALUES (?)', (username,))
            self.db.player_data_conn.commit()
            # create a new session
            sessionID = hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()
            sessions[str(sessionID)] = ConnectedClient(username, sessionID)
            logger.info("Logged in as " + username + " with session " + sessionID + "sessions: " + str(sessions))
            self.send_json_response(200, {'success': True, "session": sessionID})

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


def start_inactivity_check(timeout):
    db = DatabaseManager()
    while True:
        for _ in range(100):
            # every minute check for inactive sessions
            logger.info("Checking inactive sessions...")
            logger.info(sessions)
            current_time = time.time()
            inactive_sessions = [session_id for session_id, client in sessions.items() if current_time - client.lastActiveTime > timeout]
            
            for session_id in inactive_sessions:
                logger.info(f"Session {session_id} is inactive for too long. Removing user.")
                del sessions[session_id]
            
            time.sleep(60)

        # only once an hour check and delete guest accounts
        active_sessions = tuple(map(lambda x: x.username, list(sessions.values())))
        placeholders = ', '.join('?' for _ in active_sessions)

        db.login_cursor.execute(f'DELETE FROM login WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        db.login_conn.commit()
        db.player_data_cursor.execute(f'DELETE FROM basicPlayerData WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        db.player_data_conn.commit()
        

with ThreadedHTTPServer(("", HTTP_PORT), CustomRequestHandler) as httpd:
    print(f"HTTP server serving at port {HTTP_PORT}")
    
    # Start inactivity check in a separate thread
    inactivity_thread = threading.Thread(target=start_inactivity_check, args=(3600,))
    inactivity_thread.daemon = True
    inactivity_thread.start()

    # Start the HTTP server
    httpd.serve_forever()
