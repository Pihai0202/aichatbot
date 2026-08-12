import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import socket
import os
import sys

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve static files from static directory
        parsed = urllib.parse.urlparse(path)
        rel_path = parsed.path.lstrip("/")
        if rel_path == "" or rel_path == "index.html":
            return os.path.join(STATIC_DIR, "index.html")
        if rel_path.startswith("static/"):
            rel_path = rel_path[7:]
        return os.path.join(STATIC_DIR, rel_path)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/models":
            query = urllib.parse.parse_qs(parsed.query)
            ollama_url = query.get("url", ["http://localhost:11434"])[0].rstrip("/") + "/api/tags"
            try:
                req = urllib.request.Request(ollama_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m["name"] for m in data.get("models", [])]
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(models).encode("utf-8"))
                    return
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps([]).encode("utf-8"))
                return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                req_data = json.loads(body.decode("utf-8"))
                cfg = req_data.get("config", {})
                messages = req_data.get("messages", [])

                provider = cfg.get("provider", "ollama")
                system_prompt = cfg.get("system_prompt", "")
                temp = float(cfg.get("temperature", 0.7))
                num_ctx = int(cfg.get("num_ctx", 4096))
                repeat_penalty = float(cfg.get("repeat_penalty", 1.1))

                req_msgs = []
                if system_prompt:
                    req_msgs.append({"role": "system", "content": system_prompt})
                req_msgs.extend(messages)

                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                if provider == "ollama":
                    target_url = cfg.get("ollama_url", "http://localhost:11434").rstrip("/") + "/api/chat"
                    payload = {
                        "model": cfg.get("ollama_model", "llama3:latest"),
                        "messages": req_msgs,
                        "options": {
                            "temperature": temp,
                            "num_ctx": num_ctx,
                            "repeat_penalty": repeat_penalty
                        },
                        "stream": True
                    }
                    data_bytes = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(target_url, data=data_bytes, headers={"Content-Type": "application/json"})

                    try:
                        with urllib.request.urlopen(req, timeout=60) as resp:
                            for line in resp:
                                if line:
                                    try:
                                        chunk = json.loads(line.decode("utf-8"))
                                        token = chunk.get("message", {}).get("content", "")
                                        if token:
                                            sse_msg = f"data: {json.dumps({'token': token})}\n\n"
                                            self.wfile.write(sse_msg.encode("utf-8"))
                                            self.wfile.flush()
                                    except Exception:
                                        pass
                    except Exception as e:
                        err_msg = f"data: {json.dumps({'error': str(e)})}\n\n"
                        self.wfile.write(err_msg.encode("utf-8"))
                        self.wfile.flush()
                else:
                    target_url = cfg.get("openai_url", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
                    headers = {"Content-Type": "application/json"}
                    if cfg.get("openai_key"):
                        headers["Authorization"] = f"Bearer {cfg.get('openai_key')}"

                    payload = {
                        "model": cfg.get("openai_model", "gpt-4o-mini"),
                        "messages": req_msgs,
                        "temperature": temp,
                        "stream": True
                    }
                    data_bytes = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(target_url, data=data_bytes, headers=headers)

                    try:
                        with urllib.request.urlopen(req, timeout=60) as resp:
                            for line in resp:
                                line_str = line.decode("utf-8").strip()
                                if line_str.startswith("data: "):
                                    data_part = line_str[6:].strip()
                                    if data_part == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_part)
                                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if delta:
                                            sse_msg = f"data: {json.dumps({'token': delta})}\n\n"
                                            self.wfile.write(sse_msg.encode("utf-8"))
                                            self.wfile.flush()
                                    except Exception:
                                        pass
                    except Exception as e:
                        err_msg = f"data: {json.dumps({'error': str(e)})}\n\n"
                        self.wfile.write(err_msg.encode("utf-8"))
                        self.wfile.flush()

                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

def run_server():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    local_ip = get_local_ip()
    print("=" * 60)
    print(" [Web Server] AI Chatbot Web Remote Server Started!")
    print(f" Local Access:    http://localhost:{PORT}")
    print(f" Remote Wi-Fi IP: http://{local_ip}:{PORT}")
    print("=" * 60)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
