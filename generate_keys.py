
import base64
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def generate_vapid_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    private_bytes = private_key.private_numbers().private_value.to_bytes(32, byteorder='big')
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    return {
        'privateKey': base64.urlsafe_b64encode(private_bytes).rstrip(b'=').decode('utf-8'),
        'publicKey': base64.urlsafe_b64encode(public_bytes).rstrip(b'=').decode('utf-8')
    }

keys = generate_vapid_keys()
print("VAPID_PRIVATE_KEY =", keys['privateKey'])
print("VAPID_PUBLIC_KEY =", keys['publicKey'])
