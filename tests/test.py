#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import, division, print_function, \
    with_statement

import sys
import os
import signal
import select
import time
from subprocess import Popen, PIPE

sys.path.insert(0, './')

if sys.argv[-3] == '-c':
    client_config = sys.argv[-1]
    server_config = sys.argv[-2]
elif sys.argv[-2] == '-c':
    client_config = sys.argv[-1]
    server_config = sys.argv[-1]
else:
    raise Exception('usage: test.py -c server_conf [client_conf]')

p1 = Popen(['python', 'shadowsocks/server.py', '-c', server_config],
           stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
p2 = Popen(['python', 'shadowsocks/local.py', '-c', client_config],
           stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
p3 = None
p4 = None
p3_fin = False
p4_fin = False

# 1 shadowsocks started
# 2 curl started
# 3 curl finished
# 4 dig started
# 5 dig finished
stage = 1

try:
    local_ready = False
    server_ready = False
    fdset = [p1.stdout, p2.stdout, p1.stderr, p2.stderr]
    while True:
        r, w, e = select.select(fdset, [], fdset)
        if e:
            break

        for fd in r:
            line = fd.readline()
            if not line:
                if stage == 2 and fd == p3.stdout:
                    stage = 3
                if stage == 4 and fd == p4.stdout:
                    stage = 5
            if bytes != str:
                line = str(line, 'utf8')
            sys.stdout.write(line)
            if line.find('starting local') >= 0:
                local_ready = True
            if line.find('starting server') >= 0:
                server_ready = True

        if stage == 1:
            time.sleep(2)

            p3 = Popen(['curl', 'http://www.example.com/', '-v', '-L',
                        '--socks5-hostname', '127.0.0.1:1081',
                        '-m', '15', '--connect-timeout', '10'],
                       stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
            if p3 is not None:
                fdset.append(p3.stdout)
                fdset.append(p3.stderr)
                stage = 2
            else:
                sys.exit(1)

        if stage == 3 and p3 is not None:
            fdset.remove(p3.stdout)
            fdset.remove(p3.stderr)
            r = p3.wait()
            if r != 0:
                sys.exit(1)
            p4 = Popen(['socksify', 'dig', '@8.8.8.8', 'www.google.com'],
                       stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
            if p4 is not None:
                fdset.append(p4.stdout)
                fdset.append(p4.stderr)
                stage = 4
            else:
                sys.exit(1)

        if stage == 5:
            r = p4.wait()
            if r != 0:
                sys.exit(1)
            print('test passed')
            break
finally:
    for p in [p1, p2]:
        try:
            os.kill(p.pid, signal.SIGTERM)
        except OSError:
            pass
