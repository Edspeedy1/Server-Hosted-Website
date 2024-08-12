import RangeHTTPServer
import socketserver
import os
import time
import threading
import random
import json
import sqlite3
import bcrypt
import pymssql
from dotenv import load_dotenv
# logging for debug messages on server console
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


load_dotenv()
HTTP_PORT = int(os.getenv('PORT', 8026))

print("starting server")

server = os.getenv('DB_SERVER')
user = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
database = os.getenv('DB_DATABASE')

# Establishing the connection
DB_CONN = pymssql.connect(
    server=server,
    user=user,
    password=password,
    database=database
)

cursor = DB_CONN.cursor()
cursor.execute('SELECT TOP 50 * FROM messages ORDER BY timestamp DESC')
tempMessages = cursor.fetchall()
cursor.close()

# class for keeping track of active sessions
class ConnectedClient:
    def __init__(self, username, sessionID):
        self.username = username
        self.sessionID = sessionID
        self.lastActiveTime = time.time()
    
    def __str__(self):
        return f"username: {self.username}, sessionID: {self.sessionID}, lastActiveTime: {self.lastActiveTime}"
    def __repr__(self):
        return self.__str__()

    def update_last_active_time(self):
        self.lastActiveTime = time.time()

# legacy code, was necessary but IDK anymore and i'm too scared to touch it
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

# dictionary of active sessions
sessions = {}

# the meat and potatoes of the server
class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
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
            logger.info(str(sessions))
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
        cursor = DB_CONN.cursor()
        cursor.execute('INSERT INTO messages (username, message, timestamp) VALUES (%s, %s, %s)', (username, text, int(time.time())))
        DB_CONN.commit()
        cursor.close()

    def get_messages(self):
        cursor = DB_CONN.cursor()
        cursor.execute('SELECT TOP 50 * FROM messages ORDER BY timestamp DESC')
        tempMessages = cursor.fetchall()[::-1]
        cursor.close()
        messages = [{'username': x[1], 'message': x[2], 'timestamp': x[3]} for x in tempMessages]
        self.send_json_response(200, {'messages': messages})

    def login(self, username, password):
        logger.info("Logging in as " + username)
        hashedPassword = bcrypt.hashpw((password).encode('utf-8'), bcrypt.gensalt())
        # Check if username already exists
        cursor = DB_CONN.cursor()
        try:
            cursor.execute('SELECT * FROM loginInfo WHERE username = %s', (username,))
            usernamePass = cursor.fetchone()
            if usernamePass is not None:
                # check if password is correct
                if not bcrypt.checkpw(password.encode('utf-8'), usernamePass[1].encode('utf-8')): 
                    self.send_json_response(400, {'error': 'Incorrect password'})
                    return 
                else: # login successful
                    sessionID = random.randbytes(32).hex()
                    sessions[str(sessionID)] = ConnectedClient(username, sessionID)
                    self.send_json_response(200, {'success': True, "session": sessionID})
                    return 
            else: # new account creation
                cursor.execute('INSERT INTO loginInfo (username, password) VALUES (%s, %s)', (username, hashedPassword))
                DB_CONN.commit()
                # create a new row in the player_data table
                player_data_cursor = DB_CONN.cursor()
                player_data_cursor.execute('INSERT INTO basicPlayerData (username) VALUES (%s)', (username,))
                player_data_cursor.close()
                DB_CONN.commit()
                # create a new session
                sessionID = random.randbytes(32).hex()
                sessions[str(sessionID)] = ConnectedClient(username, sessionID)
                logger.info("Logged in as " + username + " with session " + sessionID + "sessions: " + str(sessions))
                self.send_json_response(200, {'success': True, "session": sessionID})
        finally:
            cursor.close()

    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


def start_inactivity_check(timeout):
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
        placeholders = ', '.join('%s' for _ in active_sessions)
        login_cursor = DB_CONN.cursor()
        login_cursor.execute(f'DELETE FROM login WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        DB_CONN.commit()

        player_data_cursor = DB_CONN.cursor()
        player_data_cursor.execute(f'DELETE FROM basicPlayerData WHERE username LIKE "Guest%" AND username NOT IN ({placeholders})', active_sessions)
        DB_CONN.commit()
    

with ThreadedHTTPServer(("", HTTP_PORT), CustomRequestHandler) as httpd:
    print(f"HTTP server serving at port {HTTP_PORT}")
    
    # Start inactivity check in a separate thread
    inactivity_thread = threading.Thread(target=start_inactivity_check, args=(3600,))
    inactivity_thread.daemon = True
    inactivity_thread.start()

    # Start the HTTP server
    httpd.serve_forever()
