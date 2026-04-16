import http.server
import socketserver
import json
import sqlite3
import os
import sys

PORT = 8000
DB_FILE = 'problems.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS problems
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT NOT NULL,
                  votes INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

class ProblemVoteHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
            return super().do_GET()
        
        elif self.path == '/api/problems':
            try:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id, content, votes FROM problems ORDER BY votes DESC, created_at DESC")
                rows = c.fetchall()
                conn.close()
                
                problems = [{"id": r[0], "content": r[1], "votes": r[2]} for r in rows]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                self.end_headers()
                self.wfile.write(json.dumps(problems).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"Error reading DB: {e}", file=sys.stderr)
        else:
            return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
            
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        if self.path == '/api/problems':
            content = data.get('content', '').strip()
            if content:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO problems (content, votes) VALUES (?, 0)", (content,))
                conn.commit()
                conn.close()
                self.send_response(201)
            else:
                self.send_response(400)
            self.end_headers()
            
        elif self.path == '/api/vote':
            prob_id = data.get('id')
            if prob_id is not None:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("UPDATE problems SET votes = votes + 1 WHERE id = ?", (prob_id,))
                conn.commit()
                conn.close()
                self.send_response(200)
            else:
                self.send_response(400)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    init_db()
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), ProblemVoteHandler) as httpd:
            print(f"Server started. API running on port {PORT}", file=sys.stderr)
            httpd.serve_forever()
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
