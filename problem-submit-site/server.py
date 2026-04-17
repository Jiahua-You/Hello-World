import http.server
import socketserver
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get port from environment or default to 8000
PORT = int(os.environ.get("PORT", 8000))
# Get database URL from environment
DB_URL = os.environ.get("DATABASE_URL")

# Dynamically load the correct database driver
if DB_URL:
    try:
        import psycopg2
        PARAM = "%s"
        print("Using PostgreSQL database.", file=sys.stderr)
    except ImportError:
        print("Error: psycopg2 is required for PostgreSQL but not installed.", file=sys.stderr)
        sys.exit(1)
    
    def get_db():
        return psycopg2.connect(DB_URL)
else:
    import sqlite3
    PARAM = "?"
    print("Using local SQLite database. Set DATABASE_URL for external DB.", file=sys.stderr)
    
    def get_db():
        return sqlite3.connect("problems.db")

def init_db():
    conn = get_db()
    c = conn.cursor()
    if DB_URL:
        # PostgreSQL syntax
        c.execute('''CREATE TABLE IF NOT EXISTS problems
                     (id SERIAL PRIMARY KEY,
                      content TEXT NOT NULL,
                      votes INTEGER DEFAULT 0,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    else:
        # SQLite syntax
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
                conn = get_db()
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
                try:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute(f"INSERT INTO problems (content, votes) VALUES ({PARAM}, 0)", (content,))
                    conn.commit()
                    conn.close()
                    self.send_response(201)
                except Exception as e:
                    print(f"Error inserting: {e}", file=sys.stderr)
                    self.send_response(500)
            else:
                self.send_response(400)
            self.end_headers()
            
        elif self.path == '/api/vote':
            prob_id = data.get('id')
            if prob_id is not None:
                try:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute(f"UPDATE problems SET votes = votes + 1 WHERE id = {PARAM}", (prob_id,))
                    conn.commit()
                    conn.close()
                    self.send_response(200)
                except Exception as e:
                    print(f"Error voting: {e}", file=sys.stderr)
                    self.send_response(500)
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
