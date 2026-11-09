#!/usr/bin/env python3
"""
Oyen Math - Local Development Server
Serves the Oyen Math web application on http://localhost:8080
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import json
import base64
import urllib.request
import urllib.error

def _load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v.strip().strip('"'))

_load_env()
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")

OCR_PROMPT = (
    "You are Detective Oyen, marking a Malaysian SPM Additional Mathematics student's handwritten working. "
    "Transcribe every line of working in the image in order, in plain text using ^ for powers. "
    "For each line decide if it is mathematically valid given the previous line; if not, explain the error briefly in Bahasa Melayu. "
    "Question (may be empty): {q}\n"
    "Reply with ONLY JSON: {{\"lines\":[{{\"text\":str,\"valid\":bool,\"error\":str|null}}],\"finalAnswer\":str}}. "
    "finalAnswer is the student's final answer only, in plain text (e.g. 6x+5)."
)

def run_ocr(image_data_url, question):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return 503, {"error": "ANTHROPIC_API_KEY belum ditetapkan (lihat .env.example)"}
    header, _, b64 = image_data_url.partition(",")
    media = header.split(";")[0].replace("data:", "") or "image/jpeg"
    body = {"model": MODEL, "max_tokens": 1200, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
        {"type": "text", "text": OCR_PROMPT.format(q=question[:300])}]}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = "".join(b.get("text", "") for b in json.load(r)["content"])
        a, z = text.find("{"), text.rfind("}")
        data = json.loads(text[a:z + 1])
        data["engine"] = "claude-vision"
        return 200, data
    except urllib.error.HTTPError as e:
        return 502, {"error": "Anthropic API ralat %s" % e.code}
    except Exception as e:
        return 502, {"error": "OCR gagal: %s" % e}

PORT = int(os.environ.get("PORT", 8080))
socketserver.TCPServer.allow_reuse_address = True
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == "/api/agent":
            return self._agent()
        if self.path != "/api/ocr":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", 0))
        if n > 8 * 1024 * 1024:
            code, out = 413, {"error": "Gambar terlalu besar"}
        else:
            try:
                req = json.loads(self.rfile.read(n))
                code, out = run_ocr(req.get("image", ""), req.get("question", ""))
            except Exception as e:
                code, out = 400, {"error": "Permintaan tidak sah: %s" % e}
        payload = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _agent(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            from agents.graph import run_agent
            code, out = 200, run_agent(json.loads(self.rfile.read(min(n, 200000))))
        except ImportError as e:
            code, out = 501, {"error": "Pasang kebergantungan: pip install -r requirements.txt (%s)" % e}
        except Exception as e:
            code, out = 500, {"error": "Ejen gagal: %s" % e}
        payload = json.dumps(out, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def end_headers(self):
        # Enable CORS and disable caching for smooth development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def main():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print("🐱 OYEN MATH - Local Server Running")
        print(f"📍 URL: {url}")
        print("📖 Press Ctrl+C to stop the server.")
        print("=" * 60)
        if "--open" in sys.argv:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Oyen Math server. Goodbye! Meow!")

if __name__ == "__main__":
    main()

