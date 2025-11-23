from py_vapid import Vapid
import base64
import json

v = Vapid()
v.generate_keys()

# Get the raw bytes
private_key = v.private_key
public_key = v.public_key

# Encode to base64url (without padding) for VAPID
def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

# Save to a file or print
keys = {
    "VAPID_PRIVATE_KEY": b64url(private_key),
    "VAPID_PUBLIC_KEY": b64url(public_key),
    "VAPID_CLAIM_EMAIL": "mailto:admin@silverclean.com"
}

print(json.dumps(keys, indent=4))

with open("vapid_keys.json", "w") as f:
    json.dump(keys, f, indent=4)
