# -*- coding: utf-8 -*-
from http import server as BaseHTTPServer
import re
import socket
import os
import xbmc
import xbmcvfs

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass

class BilibiliRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.addon_id = 'plugin.video.bili'
        self.chunk_size = 1024 * 64
        try:
            self.base_path = xbmc.translatePath('special://temp/%s' % self.addon_id).decode('utf-8')
        except AttributeError:
            self.base_path = xbmc.translatePath('special://temp/%s' % self.addon_id)
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        stripped_path = self.path.rstrip('/')
        if self.path.endswith('.mpd'):
            file_path = os.path.join(self.base_path, self.path.strip('/').strip('\\'))
            file_chunk = True
            try:
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml+dash')
                    self.send_header('Content-Length', os.path.getsize(file_path))
                    self.end_headers()
                    while file_chunk:
                        file_chunk = f.read(self.chunk_size)
                        if file_chunk:
                            self.wfile.write(file_chunk)
            except IOError:
                response = 'File Not Found: |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path.encode('utf-8'))
                self.send_error(404, response)


    def do_HEAD(self):
        if self.path.endswith('.mpd'):
            file_path = os.path.join(self.base_path, self.path.strip('/').strip('\\'))
            if not os.path.isfile(file_path):
                response = 'File Not Found: |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path.encode('utf-8'))
                self.send_error(404, response)
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml+dash')
                self.send_header('Content-Length', os.path.getsize(file_path))
                self.end_headers()
        else:
            self.send_error(501)


def get_http_server(address=None, port=None):
    address = address if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', address) else '0.0.0.0'
    port = int(port) if port else 54321
    try:
        server = BaseHTTPServer.HTTPServer((address, port), BilibiliRequestHandler)
        return server
    except socket.error as e:
        return None
