"""PTA server (2018 specification): TCP 11550, CUMP/LIST/PEGA/TERM.

Framing is unspecified by PTA. Two interoperable modes are supported:
* LF-delimited requests: replies OK/NOK/ARQS are LF-delimited.
* Legacy professor client: no LF in requests; short idle-gap heuristic
  determines request completion; text replies have NO trailing LF.
ARQ in BOTH modes: ASCII 'SEQ ARQ SIZE ' + exactly SIZE file bytes.
No bytes are appended to a transferred file.
"""
import select
import socket
import threading
from pathlib import Path

HOST = '127.0.0.1'
PORT = 11550
FILES = Path(__file__).resolve().parent / 'files'
USERS_FILE = Path(__file__).resolve().parent / 'users.txt'


def authorized_users():
    """Read the professor-provided username file; preserve case."""
    with USERS_FILE.open('r', encoding='utf-8-sig') as stream:
        return {line.strip() for line in stream if line.strip()}

MAX_REQUEST = 4096
QUIET_SECONDS = 0.08  # compatibility heuristic, NOT a reliable TCP framing standard
IDLE_SECONDS = 60


def requests(conn):
    """Yield (bytes, is_lf_framed); preserve split/coalesced TCP data."""
    pending = bytearray()
    while True:
        timeout = QUIET_SECONDS if pending else IDLE_SECONDS
        ready, _, _ = select.select([conn], [], [], timeout)
        if not ready:
            if pending:
                yield bytes(pending), False
                pending.clear()
                continue
            return
        chunk = conn.recv(4096)
        if not chunk:
            if pending:
                yield bytes(pending), False
            return
        pending.extend(chunk)
        while b'\n' in pending:
            line, _, rest = pending.partition(b'\n')
            pending = bytearray(rest)
            yield bytes(line).removesuffix(b'\r'), True
        if len(pending) > MAX_REQUEST:
            yield bytes(pending), False
            return


def parse(raw):
    """Return (seq, command, arg); invalid syntax retains seq when possible."""
    if len(raw) > MAX_REQUEST:
        return None, None, None
    try:
        line = raw.decode('ascii')
    except UnicodeDecodeError:
        return None, None, None
    fields = line.split(' ')
    if len(fields) < 2 or not fields[0].isascii() or not fields[0].isdecimal():
        return None, None, None
    seq = int(fields[0])
    if any(not x for x in fields):
        return seq, None, None
    cmd = fields[1]
    if cmd in ('CUMP', 'PEGA'):
        return (seq, cmd, fields[2]) if len(fields) == 3 else (seq, None, None)
    return (seq, cmd, None) if len(fields) == 2 else (seq, None, None)


def send_reply(conn, seq, status, arg=None, framed=False):
    message = f'{seq} {status}' + (f' {arg}' if arg is not None else '')
    conn.sendall(message.encode('ascii') + (b'\n' if framed else b''))


def names_in_repository():
    """PTA's unescaped comma/space delimiters cannot represent all filenames."""
    return sorted(p.name for p in FILES.iterdir()
                  if p.is_file() and p.name.isascii()
                  and ' ' not in p.name and ',' not in p.name
                  and '\n' not in p.name and '\r' not in p.name)


def handle_client(conn, address):
    state = 'WAIT_CUMP'
    last_seq = None
    print('Connected:', address)
    try:
        with conn:
            for raw, framed in requests(conn):
                seq, cmd, arg = parse(raw)
                if seq is None:
                    send_reply(conn, 0, 'NOK', framed=framed)
                    if state == 'WAIT_CUMP':
                        break
                    continue
                if last_seq is not None and seq != last_seq + 1:
                    send_reply(conn, seq, 'NOK', framed=framed)
                    if state == 'WAIT_CUMP':
                        break
                    continue
                last_seq = seq
                if state == 'WAIT_CUMP':
                    try:
                        allowed = authorized_users()
                    except (OSError, UnicodeError) as exc:
                        print('Cannot read users.txt:', exc)
                        send_reply(conn, seq, 'NOK', framed=framed)
                        break
                    if cmd != 'CUMP' or arg not in allowed:
                        send_reply(conn, seq, 'NOK', framed=framed)
                        break
                    send_reply(conn, seq, 'OK', framed=framed)
                    state = 'READY'
                    continue
                if cmd == 'LIST':
                    try:
                        names = names_in_repository()
                        arg_list = str(len(names)) + (' ' + ','.join(names) if names else '')
                        send_reply(conn, seq, 'ARQS', arg_list, framed=framed)
                    except OSError:
                        send_reply(conn, seq, 'NOK', framed=framed)
                elif cmd == 'PEGA':
                    if arg in ('.', '..') or '/' in arg or '\\' in arg:
                        send_reply(conn, seq, 'NOK', framed=framed)
                        continue
                    try:
                        f = (FILES / arg).open('rb')
                    except (OSError, ValueError):
                        send_reply(conn, seq, 'NOK', framed=framed)
                        continue
                    with f:
                        try:
                            f.seek(0, 2)
                            size = f.tell()
                            f.seek(0)
                            # One send for small files improves legacy-client interoperability;
                            # TCP can still fragment it, so this is NOT a guarantee.
                            header = f'{seq} ARQ {size} '.encode('ascii')
                            if size <= 65536:
                                conn.sendall(header + f.read())
                            else:
                                conn.sendall(header)
                                while block := f.read(65536):
                                    conn.sendall(block)
                        except OSError:
                            break  # Cannot safely send NOK after partial ARQ.
                elif cmd == 'TERM':
                    send_reply(conn, seq, 'OK', framed=framed)
                    break
                else:
                    send_reply(conn, seq, 'NOK', framed=framed)
    except (OSError, ValueError) as exc:
        print('Session error:', address, exc)
    finally:
        print('Disconnected:', address)


def serve():
    if not FILES.is_dir():
        raise SystemExit(f'Missing professor-provided files directory: {FILES}')
    if not USERS_FILE.is_file():
        raise SystemExit(f'Missing professor-provided users.txt: {USERS_FILE}')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST, PORT))
        listener.listen()
        print(f'PTA listening on {HOST}:{PORT}')
        while True:
            conn, addr = listener.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == '__main__':
    serve()
