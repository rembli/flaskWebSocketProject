# BugFix https://github.com/miguelgrinberg/Flask-SocketIO/issues/65

# from gevent import monkey
# monkey.patch_all()

# import eventlet
# eventlet.monkey_patch()

import socketio

# local dev

from app import sio as s
from app import app as a

# Integrate socket.io with WSGI
# https://python-socketio.readthedocs.io/en/latest/server.html

socketio_app = socketio.WSGIApp(s, a)
application = socketio_app.wsgi_app

if __name__ == '__main__':
    application.run()
    # s.run (a)

