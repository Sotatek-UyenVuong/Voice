import http.server
import ssl
import os

os.chdir('/home/sotatek/Documents/Uyen/demo_voice')

server_address = ('0.0.0.0', 8099)
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)

# Use existing certificates
cert_path = '/home/sotatek/Documents/Uyen/demo_voice/.cert'
httpd.socket = ssl.wrap_socket(
    httpd.socket,
    keyfile=f'{cert_path}/server-key.pem',
    certfile=f'{cert_path}/server-cert.pem',
    server_side=True
)

print(f'🔒 HTTPS Server running on https://0.0.0.0:8099')
print(f'📱 Access from other devices: https://192.168.200.22:8099/Homepage.html')
httpd.serve_forever()
