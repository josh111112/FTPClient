from socket import socket, AF_INET, SOCK_STREAM

DEFAULT_FTP_PORT = 21
FTP_SERVER = "ftp.cs.brown.edu"

def _readline(sock: socket) -> str:
    data = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Server closed connection while reading line")
        data += chunk
        if chunk == b'\n':
            break
    return data.decode(errors="replace").rstrip('\r\n')

def parse_host_port(s: str, default_port: int = DEFAULT_FTP_PORT):
    s = s.strip()
    if not s:
        raise ValueError("Empty host string")

    if ':' in s:
        host, port_str = s.rsplit(':', 1)
        host = host.strip()
        if not host:
            raise ValueError(f"Missing hostname in '{s}'")
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port '{port_str}' in '{s}'")
    else:
        host = s
        port = default_port

    return host, port

def connect_control(host: str, port: int):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))
    
    code, _ = read_response(sock)  # greeting
    if code != 220:
        print(f"Warning: unexpected greeting code {code}")
    #print(msg)
    return sock

def login():
    print("In progress...")

def quit(sock: socket):
    try:
        send_command(sock, "QUIT")
        # Read the final reply (usually 221 Goodbye)
        read_response(sock)
    except OSError as e:
        # If something goes wrong during QUIT, still close the socket.
        print(f"Error during QUIT: {e}")
    finally:
        sock.close()

def cmd_loop():
    print("In progress...")

def send_command(sock: socket, cmd: str):
    line = (cmd + "\r\n").encode("ascii", errors="replace")
    sock.sendall(line)

def read_response(sock: socket):
    # read first line for response code
    first = _readline(sock)
    if len(first) < 3 or not first[:3].isdigit():
        raise ValueError(f"Malformed reply: {first!r}")
    
    code = first[:3]
    lines = [first]

    if len(first) >= 4 and first[3] == '-':
        while True:
            line = _readline(sock)
            lines.append(line)
            if line.startswith(code + " "):
                break

    for line in lines:
        print(f" -*- {line}")

    return int(code), "\n".join(lines)

def open_data_conn_pasv():
    print("In progress...")

def do_list():
    print("In progress...")

def do_get():
    print("In progress...")

def do_put():
    print("In progress...")

