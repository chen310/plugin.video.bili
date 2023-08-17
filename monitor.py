# -*- coding: utf-8 -*-
import os
import shutil
import threading
import xbmc
import xbmcvfs
import xbmcaddon

from http_server import get_http_server

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass


class BilibiliMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.addon_id = 'plugin.video.bili'
        self._httpd_port = int(xbmcaddon.Addon(self.addon_id).getSetting('server_port'))
        self._httpd_address = '0.0.0.0'
        self.httpd = None
        self.httpd_thread = None

        self.start_httpd()

    def start_httpd(self):
        if not self.httpd:
            self.httpd = get_http_server(address=self._httpd_address, port=self._httpd_port)
            if self.httpd:
                self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
                self.httpd_thread.daemon = True
                self.httpd_thread.start()

    def shutdown_httpd(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.httpd_thread.join()
            self.httpd_thread = None
            self.httpd = None

    def restart_httpd(self):
        self.shutdown_httpd()
        self.start_httpd()

    def remove_temp_dir(self):
        try:
            path = xbmc.translatePath('special://temp/%s' % self.addon_id).decode('utf-8')
        except AttributeError:
            path = xbmc.translatePath('special://temp/%s' % self.addon_id)

        if os.path.isdir(path):
            try:
                xbmcvfs.rmdir(path, force=True)
            except:
                pass
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
            except:
                pass

        if os.path.isdir(path):
            return False
        else:
            return True