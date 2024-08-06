import RangeHTTPServer
import socketserver
import os
import time
import threading
import random
import json
import sqlite3

PORT = int(os.getenv('PORT', 8026))

print("starting server")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class CustomRequestHandler(RangeHTTPServer.RangeRequestHandler):
    def __init__(self, request, client_address, server):
        self.CONN = sqlite3.connect('chatroom-database.db')
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
            print(post_data)
            data = json.loads(post_data)
            self.upload_message(data['username'], data['text'], data['roomid'])
            self.send_json_response(200, {'success': True})
        elif self.path == '/get_messages':
            roomid = self.headers['roomid']
            self.get_messages(roomid)

    def upload_message(self, username, text, roomid):
        self.C.execute('INSERT INTO messages (username, message, room_name, timestamp) VALUES (?, ?, ?, ?)', (username, text, roomid, int(time.time())))
        self.CONN.commit()

    def get_messages(self, roomid):
        if self.C.execute('SELECT EXISTS(SELECT 1 FROM messages WHERE room_name = ?)', (roomid,)).fetchone()[0]:
            messages = self.C.execute('SELECT * FROM messages WHERE room_name = ? ORDER BY timestamp', (roomid,)).fetchall()
            messages = [{'username': x[2], 'message': x[3], 'timestamp': x[4]} for x in messages]
            self.send_json_response(200, {'messages': messages})
        else:
            self.send_json_response(200, {'messages': []})


    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

with ThreadedHTTPServer(("", PORT), CustomRequestHandler) as httpd:
    print("serving at port", PORT)
    # Start a new thread for serving requests
    for i in range(10):
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True  # Daemonize the thread so it exits when the main thread exits
        server_thread.start()
        # Wait for the server thread to finish (if ever)
        server_thread.join()