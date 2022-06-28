import hmac
import hashlib
import binascii

def get_hash(msg_bytes):
    dig = hmac.new(b'1234567890', msg=msg_bytes, digestmod=hashlib.sha256).digest()
    return binascii.hexlify(dig).decode('ascii')


