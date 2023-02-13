#!/usr/bin/env python3
from flask import Flask, render_template, session, abort
from flask_session import Session
from flask_socketio import SocketIO, disconnect, rooms
import pty
import os
import select
import termios
import struct
import fcntl
import psutil
import subprocess
from config import TERM_INIT_CONFIG


__author__ = "fisherworks.cn" #based on flask_term_remote on github

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="")
app.config["SECRET_KEY"] = "the top secret!"
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
# according to blog post of Miguel Grinberg, the author of Flask-SocketIO
# manage_session should be set to False, only if you have server_side session
# and you also want a bi-directional sharing of session between Flask and Flask-SocketIO
socketio = SocketIO(app, manage_session=False, logger=False, engineio_logger=False)


def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def read_and_forward_pty_output(fd=None, pid=None, room_id=None):
    """
    read data on pty master from the pty slave, and emit to the web terminal visitor
    """
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.15)
        # using flask default web server, or uwsgi production web server
        # when the child process is terminated, it will not disappear from linux process list
        # and keep staying as a zombie process until the parent exits.
        try:
            child_process = psutil.Process(pid)
        except psutil.NoSuchProcess as err:
            return
        if child_process.status() not in ('running', 'sleeping'):
            return
        # print('background running')
        if fd:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
            if data_ready:
                # output = os.read(fd, max_read_bytes).decode('ascii')
                try:
                    output = os.read(fd, max_read_bytes).decode()
                except Exception as err:
                    output = """
                    ***AQUI WEB TERM ERR***
                    {}
                    ***********************
                    """.format(err)
                # the key for different visitor to get different terminal (instead of mixing up)
                # is to let the background task push pty response to each one's own (default) ROOM!
                socketio.emit("pty-output", {"output": output}, namespace="/pty", room=room_id)


@app.route("/")
def index():
    return 'this is working'


@app.route("/remote/<string:term_type>/<string:username>/<int:port>", methods=['GET'])
def remote_conn(term_type, username, port):
    # put uname and port into session of every single visitor
    if term_type not in ('ssh', 'telnet'):
        return abort(404, 'wrong terminal type, can only be either ssh or telnet')
    session['terminal_config'] = TERM_INIT_CONFIG
    session['terminal_config']['term_type'] = term_type
    session['terminal_config']['username'] = username
    session['terminal_config']['port'] = port
    session.modified = True
    return render_template("index.html")


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    """write to the child pty, which now is the ssh process from this machine to the 'domain' configured
    """
    try:
        child_process = psutil.Process(session.get('terminal_config').get('child_pid'))
    except psutil.NoSuchProcess as err:
        disconnect()
        session['terminal_config'] = TERM_INIT_CONFIG
        return
    if child_process.status() not in ('running', 'sleeping'):
        disconnect()
        session['terminal_config'] = TERM_INIT_CONFIG
        return
    # print(session)
    # print(data, 'from input')
    fd = session.get('terminal_config').get('fd')
    if fd:
        # print("writing to ptd: %s" % data["input"])
        # os.write(fd, data["input"].encode('ascii'))
        os.write(fd, data["input"].encode())


@socketio.on("resize", namespace="/pty")
def resize(data):
    try:
        child_process = psutil.Process(session.get('terminal_config').get('child_pid'))
    except psutil.NoSuchProcess as err:
        disconnect()
        session['terminal_config'] = TERM_INIT_CONFIG
        return
    if child_process.status() not in ('running', 'sleeping'):
        disconnect()
        session['terminal_config'] = TERM_INIT_CONFIG
        return
    fd = session.get('terminal_config').get('fd')
    if fd:
        set_winsize(fd, data["rows"], data["cols"])


@socketio.on("connect", namespace="/pty")
def pty_connect():
    """new client connected"""

    if session.get('terminal_config', {}).get('child_pid', None):
        print(session['terminal_config']['child_pid'])
        # already started child process, don't start another
        return

    # create child process attached to a pty we can read from and write to
    (child_pid, fd) = pty.fork()
    if child_pid == 0:
        # this is the child process fork.
        # anything printed here will show up in the pty, including the output
        # of this subprocess
        # subprocess.run('bash')
        term_type = session.get('terminal_config').get('term_type')
        path = TERM_INIT_CONFIG.get('client_path', {}).get(term_type, None)
        if not path:
            print("Can't locate {} binary, exit".format(term_type))
            disconnect()
        if term_type == 'telnet':
            # switch to the right location of your telnet binary (example comes from OSX which got telnet from brew)
            # or you can also make work like auto-detection, or manually but configurable
            os.execl(path, 'telnet', '-l', session['terminal_config']['username'],
                     session['terminal_config']['domain'], '{}'.format(session['terminal_config']['port']))
        elif term_type == 'ssh':
            # switch to the right location of your ssh binary
            # or you can also make work like auto-detection, or manually but configurable
            os.execl(path, 'ssh', '-p',
                     '{}'.format(session['terminal_config']['port']),
                     '{}@{}'.format(session['terminal_config']['username'], session['terminal_config']['domain']))
        else:
            app.logger.debug("wrong term type {}".format(term_type))
            disconnect()
            session['terminal_config'] = TERM_INIT_CONFIG
    else:
        # this is the parent process fork.
        # store child fd and pid in session
        # which means different visitor get different pid, fd, and its own room (by default)
        session['terminal_config']['fd'] = fd
        session['terminal_config']['child_pid'] = child_pid
        session['terminal_config']['room_id'] = rooms()[0]
        # in this article https://overiq.com/flask-101/sessions-in-flask/
        # it said that if a mutable data structure need to be set in the flask session
        # we have to use session.modified = True to explicitly let flask know it
        session.modified = True
        set_winsize(fd, 50, 50)
        app.logger.debug("child pid = {}".format(child_pid))
        app.logger.debug("rooms of this session = {}".format(rooms()))
        socketio.start_background_task(read_and_forward_pty_output, fd, child_pid, rooms()[0])
        app.logger.debug("background task running")
        # print(session)


@socketio.on('disconnect', namespace='/pty')
def pty_disconnect():
    try:
        child_process = psutil.Process(session.get('terminal_config', {}).get('child_pid'))
    except psutil.NoSuchProcess as err:
        disconnect()
        session['terminal_config'] = TERM_INIT_CONFIG
        return
    if child_process.status() in ('running', 'sleeping'):
        # if visitor just close the browser tab then left alone the pty here
        # it should be terminated by the parent process after
        child_process.terminate()
        app.logger.debug('user left the pty alone, terminated')
    app.logger.debug('Client disconnected')


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)
