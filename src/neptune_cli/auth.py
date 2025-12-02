def serve_callback_handler():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    """Start a local HTTP server to wait for the OAuth callback"""

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Login successful! You can close this window.")
            # Extract access token from the URL "token" query parameter
            from urllib.parse import urlparse, parse_qs

            query_components = parse_qs(urlparse(self.path).query)
            if "token" in query_components:
                access_token = query_components["token"][0]
                self.server.access_token = access_token
            else:
                self.server.access_token = None
            self.server.callback_received = True

        def log_message(self, format, *args):
            return  # Suppress logging

    server_address = ("localhost", 0)  # Bind to an available port
    httpd = HTTPServer(server_address, CallbackHandler)
    port = httpd.server_port

    def run_server():
        while not getattr(httpd, "callback_received", False):
            httpd.handle_request()

    thread = threading.Thread(target=run_server)
    thread.start()
    return port, httpd, thread
