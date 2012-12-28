import socket, re
from srcdspy.util import *

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2

SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

MAX_COMMAND_LENGTH = 510

MIN_MESSAGE_LENGTH = 4 + 4 + 1 + 1
MAX_MESSAGE_LENGTH = 4 + 4 + 4096 + 1

PROBABLY_SPLIT_IF_LARGER_THAN = MAX_MESSAGE_LENGTH - 400

RCON_EMPTY_RESP = (10,0,0,'','')

MESSAGE_TERMINATOR = '\x00'

class RconException(Exception):
    pass

class SourceRcon(object):
    def __init__(self):
        self.req_id = 0
        self.address = None
        self.authed = False

    def connect(self, address, password):
        self.tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = address
        self.tcpsock.connect(address)
        self._auth(password)

    def _auth(self, password):
        req_id = self._send(SERVERDATA_AUTH, password)
        result = RCON_EMPTY_RESP
        while result != (10, req_id, SERVERDATA_AUTH_RESPONSE, '', ''):
            result = self._receive()
            if result[1] == -1:
                raise RconException
        self.password = password

    def close(self):
        self.tcpsock.close()
        self.authed = False

    def _send(self, command, message):
        self.req_id += 1
        raw = (pack_long(self.req_id) + pack_long(command) + message +
            ''.join([MESSAGE_TERMINATOR] * 2))
        raw = pack_long(len(raw)) + raw
        self.tcpsock.send(raw)
        return self.req_id

    def _receive(self):
        raw_packetlen = self.tcpsock.recv(4)
        packetlen, raw = unpack_long(raw_packetlen)
        raw = self.tcpsock.recv(packetlen)
        req_id, raw = unpack_long(raw)
        command, raw = unpack_long(raw)
        if len(raw) == 2:
            return packetlen, req_id, command, '', ''
        else:
            a, b = raw.split('\x00', 1)
            return packetlen, req_id, command, a, b[:-1]

    def rcon(self, command, retries=1):
        # Send whole scripts
        if '\n' in command:
            commands = command.split('\n')
            def f(x): y = x.strip(); return len(y) and not y.startswith("//")
            commands = filter(f, commands)
            results = map(self.rcon, commands)
            return ''.join(results)

        while retries >= 0:
            try:
                self._send(SERVERDATA_EXECCOMMAND, command)
                resp = self._receive()
                return ''.join(resp[-2:])
            except Exception as e:
                retries -= 1
                address = self.address
                password = self.password
                self.close()
                self.connect(address, password)

        raise RconException
