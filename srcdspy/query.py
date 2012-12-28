import socket
from srcdspy.util import *

PACKETSIZE = 1400

# Is the response split among many packets or just one?
WHOLE = -1
SPLIT = -2

# Challenge
CHALLENGE = -1
S2C_CHALLENGE = 'A'

# Details Query
A2S_INFO = 'T'
A2S_INFO_STRING = 'Source Engine Query'
A2S_INFO_RESP = 'I'

# Players Query
A2S_PLAYER = 'U'
A2S_PLAYER_RESP = 'D'

# Rules Query
A2S_RULES = 'V'
A2S_RULES_RESP = 'E'

def get_challenge(data):
    typ, data = unpack_byte(data)
    if typ == ord(S2C_CHALLENGE):
        return unpack_long(data)[0]

class QueryException(Exception):
    pass

class SourceQuery(object):
    def __init__(self):
        self.udpsock = None

    def connect(self, address):
        self.udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpsock.connect(address)

    def close(self):
        self.udpsock.close()

    def _receive(self):
        raw = self.udpsock.recv(PACKETSIZE)
        typ, raw = unpack_long(raw)
        if typ == WHOLE:
            return raw
        elif typ == SPLIT:
            resp_id, raw = unpack_long(raw)
            total, raw = unpack_byte(raw)
            num, raw = unpack_byte(raw)
            splitsize, raw = unpack_short(raw)
            result = [None] * total
            result[num] = raw

            while not all(result):
                raw = self.udpsock.recv(PACKETSIZE)
                inner_typ, raw = unpack_long(raw)
                inner_resp_id, raw = unpack_long(raw)
                if inner_typ == SPLIT and inner_resp_id == resp_id:
                    total, raw = unpack_byte(raw)
                    num, raw = unpack_byte(raw)
                    splitsize, raw = unpack_byte(raw)
                    result[num] = raw
                else:
                    raise QueryException
            combined = ''.join(result)
            typ, combined = unpack_long(combined)
            if typ == WHOLE:
                return combined
            else:
                raise SourceException

    def info(self):
        self.udpsock.send(pack_long(WHOLE) + A2S_INFO +
                pack_string(A2S_INFO_STRING))
        raw = self._receive()
        typ, raw = unpack_byte(raw)
        if typ == ord(A2S_INFO_RESP):
            result = {}

            result['network_version'], raw = unpack_byte(raw)
            result['hostname'], raw = unpack_string(raw)
            result['map'], raw = unpack_string(raw)
            result['gamedir'], raw = unpack_string(raw)
            result['gamedesc'], raw = unpack_string(raw)
            result['appid'], raw = unpack_short(raw)
            result['numplayers'], raw = unpack_byte(raw)
            result['maxplayers'], raw = unpack_byte(raw)
            result['numbots'], raw = unpack_byte(raw)
            result['dedicated'], raw = unpack_byte(raw)
            result['os'], raw = unpack_byte(raw)
            result['passworded'], raw = unpack_byte(raw)
            result['secure'], raw = unpack_byte(raw)
            result['version'], raw = unpack_string(raw)

            try:
                edf, raw = unpack_byte(raw)
                result['edf'] = edf

                if edf & 0x80:
                    result['port'], raw = unpack_short(raw)
                if edf & 0x10:
                    result['steamid'], raw = unpack_longlong(raw)
                if edf & 0x40:
                    result['specport'], raw = unpack_short(raw)
                    result['specname'], raw = unpack_string(raw)
                if edf & 0x20:
                    result['tag'], raw = unpack_string(raw)
            except:
                # Explosions!
                pass

            return result
        else:
            raise QueryException

    def player(self):
        self.udpsock.send(pack_long(WHOLE) + A2S_PLAYER + pack_long(CHALLENGE))
        raw = self._receive()
        challenge = get_challenge(raw)

        self.udpsock.send(pack_long(WHOLE) + A2S_PLAYER + pack_long(challenge))
        raw = self._receive()
        typ, raw = unpack_byte(raw)
        if typ == ord(A2S_PLAYER_RESP):
            num_players, raw = unpack_byte(raw)

            result = []

            # Cheaty 32-slot servers may send an incomplete reply, jerks
            try:
                for i in xrange(num_players):
                    player = {}
                    player['index'], raw = unpack_byte(raw)
                    player['name'], raw = unpack_string(raw)
                    player['kills'], raw = unpack_long(raw)
                    player['time'], raw = unpack_float(raw)
                    result.append(player)
            except:
                # Explosions!
                pass

            return result
        else:
            raise QueryException

    def rules(self):
        self.udpsock.send(pack_long(WHOLE) + A2S_RULES + pack_long(CHALLENGE))
        raw = self._receive()
        challenge = get_challenge(raw)

        self.udpsock.send(pack_long(WHOLE) + A2S_RULES + pack_long(challenge))
        raw = self._receive()
        typ, raw = unpack_byte(raw)
        if typ != ord(A2S_RULES):
            rules = {}
            numrules, raw = unpack_short(raw)

            # TF2 sends incomplete packets so numrules is a lie, maybe
            while len(raw) > 0:
                try:
                    key, raw = unpack_string(raw)
                    rules[key], raw = unpack_string(raw)
                except:
                    # Explosions!
                    pass
            return rules
        else:
            raise QueryException
