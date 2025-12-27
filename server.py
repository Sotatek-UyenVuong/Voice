#!/usr/bin/env python3
"""
Token server for LiveKit Voice Agent web client with Explicit Agent Dispatch
Serves token generation API at https://localhost:8088
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import ssl
import asyncio
import threading
from livekit.api import AccessToken, VideoGrants, LiveKitAPI, CreateAgentDispatchRequest
from dotenv import load_dotenv

load_dotenv()

# Agent configuration
AGENT_NAME = "restaurant-bot"

async def dispatch_agent_to_room(room_name: str, metadata: dict = None):
    """
    Dispatch agent to room using explicit dispatch
    This runs asynchronously after token generation
    """
    lk_api = LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET")
    )
    
    try:
        print(f"🤖 Dispatching agent '{AGENT_NAME}' to room {room_name}...")
        await lk_api.agent_dispatch.create_dispatch(
            CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=json.dumps(metadata or {})
            )
        )
        print(f"✅ Agent '{AGENT_NAME}' dispatched to room {room_name}!")
    except Exception as dispatch_error:
        print(f"❌ Agent dispatch failed: {dispatch_error}")
        # Don't fail - agent might auto-join anyway
    finally:
        await lk_api.aclose()


def dispatch_agent_background(room_name: str, metadata: dict = None):
    """
    Run agent dispatch in background thread
    """
    def run_async():
        asyncio.run(dispatch_agent_to_room(room_name, metadata))
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()


class TokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/token':
            self.handle_token_request(parsed_path)
        else:
            self.send_error(404, "Not Found")
    
    def handle_token_request(self, parsed_path):
        """Generate and return a LiveKit access token"""
        try:
            # Parse query parameters
            params = parse_qs(parsed_path.query)
            room_name = params.get('room', ['default-room'])[0]
            participant_name = params.get('name', ['user'])[0]
            
            # Get LiveKit credentials
            api_key = os.getenv("LIVEKIT_API_KEY")
            api_secret = os.getenv("LIVEKIT_API_SECRET")
            livekit_url = os.getenv("LIVEKIT_URL")
            
            if not api_key or not api_secret:
                raise ValueError("Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET")
            
            # Generate token
            token = AccessToken(api_key, api_secret)
            token.with_identity(participant_name)
            token.with_name(participant_name)
            token.with_grants(
                VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            
            jwt_token = token.to_jwt()
            
            # Send response
            response = {
                "token": jwt_token,
                "url": livekit_url,
                "room": room_name,
                "name": participant_name
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            self.wfile.write(json.dumps(response).encode())
            
            print(f"✅ Token generated for room={room_name}, name={participant_name}")
            
            # Dispatch agent to room (explicit dispatch)
            dispatch_agent_background(
                room_name=room_name,
                metadata={
                    "participant_name": participant_name,
                    "timestamp": str(os.times().elapsed)
                }
            )
            
        except Exception as e:
            print(f"❌ Error generating token: {e}")
            self.send_error(500, str(e))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.date_time_string()}] {format % args}")


def main():
    PORT = 8088
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, TokenHandler)
    
    # Enable HTTPS
    cert_file = os.path.join(os.path.dirname(__file__), '.cert/server-cert.pem')
    key_file = os.path.join(os.path.dirname(__file__), '.cert/server-key.pem')
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(cert_file, key_file)
        httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
        protocol = "https"
        print("🔒 HTTPS enabled")
    else:
        protocol = "http"
        print("⚠️  Running without HTTPS (cert files not found)")
    
    print("\n" + "="*70)
    print("🚀 LiveKit Token Server Started")
    print("="*70)
    print(f"\n📡 Server running at: {protocol}://0.0.0.0:{PORT}")
    print(f"🔗 Token endpoint: {protocol}://192.168.200.22:{PORT}/api/token?room=<room>&name=<name>")
    print("\nExample:")
    print(f"   {protocol}://192.168.200.22:{PORT}/api/token?room=test-room&name=web-user")
    print("\n" + "="*70)
    print("\n⏳ Waiting for requests... (Press Ctrl+C to stop)\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        httpd.shutdown()


if __name__ == "__main__":
    main()
