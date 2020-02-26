# Flask Web Terminal to Remote
A web terminal to access certain remote ssh/telnet server with multi-user support

[README 中文版](http://fisherworks.cn/?p=2848)

![screenshot](https://github.com/Fisherworks/flask-remote-terminal/blob/master/flask_remote_term_demo.jpg)

## What makes this unique
* Created for remote access and remote-only, instead of wandering on the local
* Telnet and SSH client only (for now), can be added further (but still well controlled)
* Made to access certain/specific target only (setup in config), away from being sidekick of villains
* Multiple users supported by (server-side) session based key info storage

![sys_chart](https://github.com/Fisherworks/flask-remote-terminal/blob/master/flask_remote_term_chart.png)

## Based on
* A concept from github repo [pyxterm.js](https://github.com/cs01/pyxterm.js) by [cs01](https://github.com/cs01)


## Use cases of this "weirdo"
A handy (web) console to manage a certain intermediate host which has its bunch ports proxying the targets that really matter
* Like all web terminals, the only thing needed is a web browser (that has support to websocket), no client (such as putty) installation needed
* Target of the web console can reach should be limited to the designated (things like a gateway) only
* Use cases should also be well controlled, such as telnet and ssh here, as limited options
* Local server that provide this web console should NOT be easily messed around


## Progress
A meaningful prototype that works

## Meanings
And beside what's mentioned in [pyxterm.js](https://github.com/cs01/pyxterm.js#why) -

* learn to import [server-side session](https://blog.miguelgrinberg.com/post/flask-socketio-and-the-user-session) (by flask-session) to serve multiple users
* Use the [default rooms of socketio](https://github.com/miguelgrinberg/Flask-SocketIO/tree/master/example) to split the backends for different visitors


## Deployment

Clone this repository, get into the folder, then run:

```
python3 -m venv venv  # must be python3.6+
venv/bin/pip install -r requirements.txt
```
Now copy the file `config_sample.py` to `config.py`, then edit the `domain` to be your remote target, either ip addr or domain name should work.

Make sure you have the telnet and/or ssh client binary installed on the server, with absolute paths here in the config. 
For example, if the server OS is macOS, and telnet was installed through Brew, then the telnet path could be `/usr/local/bin/telnet`

Example:
```
TERM_INIT_CONFIG = {
    'domain': 'example.com', # or ip address like 192.168.10.11
    'client_path': {
        'telnet': '/usr/bin/telnet', # confirmed location of your client binary (with cmd like 'which telnet')
        'ssh': '/usr/bin/ssh'
    }
}
```
Run `python app.py` or `gunicorn -b 0.0.0.0:5000 -k gevent -w 1 app:app`

Visit `http://127.0.0.1:5000/remote/<method>/<username>/<port>` to try it.

Example:
```
http://127.0.0.1:5000/remote/ssh/usertest/6022  # ssh -p 6022 usertest@192.168.11.111
http://127.0.0.1:5000/remote/telnet/usertest/7023  # telnet -l usertest 192.168.11.111 7023
```

## Known issue(s)
* This can also be served by `uwsgi --socket :5000 --gevent 1000 --master --wsgi-file=./app.py --callable app` as a more friendly production deployment, but the telnet part won't survive by unknown cause while the ssh works quite well. If anyone can get this resolved, pls let me know - this is a better option for integration with nginx, as far as I know.
* Don't even consider to run the server with more than 1 worker, no matter through uwsgi or gunicorn, unless consideration of phasing in a message queue. Talking about this here is beyond the scope, feel free to find out the documents from [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/#using-multiple-workers). 
