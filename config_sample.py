TERM_INIT_CONFIG = {
    # instead of local server runnning this web terminal service
    # "domain" is the target that you want to access through local server (with this web terminal)
    # and before doing so - make sure you have username and port (on the "domain") to implement remote access
    'domain': 'example.com', # or ip address like 192.168.10.11
    'client_path': {
        'telnet': '/usr/local/bin/telnet', # confirmed location of your client binary (with cmd like 'which telnet')
        'ssh': '/usr/bin/ssh'
    }
}