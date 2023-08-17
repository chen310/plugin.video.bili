# -*- coding: utf-8 -*-
from monitor import BilibiliMonitor


def run():
    sleep_time = 10
    monitor = BilibiliMonitor()

    monitor.remove_temp_dir()

    while not monitor.abortRequested():
        if monitor.waitForAbort(sleep_time):
            break

    if monitor.httpd:
        monitor.shutdown_httpd()


if __name__ == '__main__':
    run()
