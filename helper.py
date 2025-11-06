from socket import socket, AF_INET, SOCK_STREAM
import getpass
import threading

DEFAULT_FTP_PORT = 21
FTP_SERVER = "ftp.cs.brown.edu"
BUFFER_SIZE = 4092

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

    return sock

def login(sock: socket) -> bool:
    username = input("Username: ").strip()
    send_command(sock, f"USER {username}")

    code, msg = read_response(sock)
    if code == 230:
        print("Logged in successfully.")
        return True
    
    if code != 331:
        print(f"Unexpected reply to USER: {code} {msg}")
        return False
    
    password = getpass.getpass("Password: ")
    send_command(sock, f"PASS {password}")
    code, msg = read_response(sock)
    if code == 230:
        print("Logged in successfully.")
        return True
    else:
        return False

def quit(sock: socket):
    try:
        send_command(sock, "QUIT")
        # Read the final reply (usually 221 Goodbye)
        code, msg = read_response(sock)
        print(f"Server final reply: {code} {msg}")

    except OSError as e:
        # If something goes wrong during QUIT, still close the socket.
        print(f"Error during QUIT: {e}")
    finally:
        sock.close()

def cmd_loop(sock: socket):
    # Command loop: ls, cwd, get, put, close, quit
    print("Commands: ls, cwd <dir>, get <remote> [local], put <local> [remote], close, quit")
    while True:
        try:
            line = input("ftp> ").strip()
        except EOFError:
            print()
            quit(sock)
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "close"):
            # Disconnect & exit program
            quit(sock)
            break
        elif cmd == "ls":
            do_list(sock)
        elif cmd == "cwd":
            if len(parts) < 2:
                print("Usage: cwd <directory>")
                continue
            do_cwd(sock, parts[1])
        elif cmd == "get":
            if len(parts) < 2:
                print("Usage: get <remote> [local]")
                continue
            remote = parts[1]
            local = parts[2] if len(parts) >= 3 else None
            do_get(sock, remote, local)
        elif cmd == "put":
            if len(parts) < 2:
                print("Usage: put <local> [remote]")
                continue
            local = parts[1]
            remote = parts[2] if len(parts) >= 3 else None
            do_put(sock, local, remote)
        else:
            print(f"Unknown command: {cmd}")

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
        print(f" > {line}")

    return int(code), "\n".join(lines)

def open_data_conn_pasv(sock: socket):
    send_command(sock, "PASV")
    code, msg = read_response(sock)
    if code != 227:
        print(f"PASV failed with code {code}")
        return None
    start = msg.find('(')
    end = msg.find(')', start + 1)
    if start == -1 or end == -1:
        print("Could not parse PASV reply")
        return None

    nums = msg[start + 1:end].split(',')
    if len(nums) != 6:
        print("Could not parse PASV host/port")
        return None

    try:
        h1, h2, h3, h4, p1, p2 = [n.strip() for n in nums]
        host = ".".join([h1, h2, h3, h4])
        port = int(p1) * 256 + int(p2)
    except ValueError:
        print("Invalid numbers in PASV reply")
        return None

    dsock = socket(AF_INET, SOCK_STREAM)
    dsock.connect((host, port))
    return dsock 

def do_list(sock: socket):
    # Listing files (ls)
    dsock = open_data_conn_pasv(sock)
    if dsock is None:
        return

    send_command(sock, "LIST")
    code1, _ = read_response(sock)
    if 100 <= code1 < 200:
        pass
    elif code1 >= 400:
        print(f"LIST failed with code {code1}")
        dsock.close()
        return
    else:
        print(f"Unexpected LIST reply code {code1}")
        dsock.close()
        return

    try:
        while True:
            data = dsock.recv(BUFFER_SIZE)
            if not data:
                break
            print(data.decode(errors="replace"), end='')
    finally:
        dsock.close()

    code2, _ = read_response(sock)
    if code2 not in (226, 250):
        print(f"LIST finished with code {code2}")

def do_cwd(sock: socket, path: str):
    # Changing remote directory
    send_command(sock, f"CWD {path}")
    code, _ = read_response(sock)
    if code != 250:
        print(f"Failed to change directory, code {code}")

def do_get(sock, remote, local=None):
    # Downloading files
    if local is None:
        local = remote

    dsock = open_data_conn_pasv(sock)
    if dsock is None:
        return

    send_command(sock, f"RETR {remote}")
    code1, _ = read_response(sock)
    if 100 <= code1 < 200:
        pass
    elif code1 >= 400:
        # downloading non-existing remote file
        print(f"RETR failed with code {code1}")
        dsock.close()
        return
    else:
        print(f"Unexpected RETR reply code {code1}")
        dsock.close()
        return

    try:
        f = open(local, "wb")
    except OSError as e:
        print(f"Error opening local file '{local}' for writing: {e}")
        dsock.close()
        return

    # Use a worker thread for the data transfer
    def _worker():
        try:
            while True:
                chunk = dsock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                f.write(chunk)
        finally:
            dsock.close()
            f.close()

    t = threading.Thread(target=_worker)
    t.start()
    t.join()

    code2, _ = read_response(sock)
    if code2 not in (226, 250):
        print(f"Download finished with code {code2}")

def do_put(sock, local, remote=None):
    # Upload files
    if remote is None:
        remote = local

    try:
        f = open(local, "rb")
    except FileNotFoundError:
        print(f"Local file '{local}' not found")
        return
    except OSError as e:
        print(f"Error opening local file '{local}': {e}")
        return

    dsock = open_data_conn_pasv(sock)
    if dsock is None:
        f.close()
        return

    send_command(sock, f"STOR {remote}")
    code1, _ = read_response(sock)
    if 100 <= code1 < 200:
        pass
    elif code1 >= 400:
        print(f"STOR failed with code {code1}")
        dsock.close()
        f.close()
        return
    else:
        print(f"Unexpected STOR reply code {code1}")
        dsock.close()
        f.close()
        return

    # Use a worker thread for the upload
    def _worker():
        try:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                dsock.sendall(chunk)
        finally:
            dsock.close()
            f.close()

    t = threading.Thread(target=_worker)
    t.start()
    t.join()

    code2, _ = read_response(sock)
    if code2 not in (226, 250):
        print(f"Upload finished with code {code2}")