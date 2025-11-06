import sys
from helper import *

def get_host_port_from_argv(argv):
    if len(argv) < 2:
        # no argument → use defaults
        host = FTP_SERVER
        port = DEFAULT_FTP_PORT
        print(f"No host given, defaulting to {host}:{port}")
    else:
        # argument present → parse it
        host, port = parse_host_port(argv[1])
    return host, port

def main():

    host, port = get_host_port_from_argv(sys.argv)
    print(f"Connecting to {host} on port {port}")
    
    try:
        ctrl_sock = connect_control(host, port)
    except OSError as e:
        print(f"Error connecting to {host}:{port} -> {e}")
        return

    if not login(ctrl_sock):
        print("Login failed.")
        quit(ctrl_sock)
        return

    cmd_loop(ctrl_sock)
    
if __name__ == "__main__":
    main()