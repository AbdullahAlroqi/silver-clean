from pywebpush import webpush
import os
import base64

# Attempt to generate keys using a helper if available, otherwise use cryptography
try:
    # This is a common way to generate keys if the library supports it directly or via CLI
    # But let's use os.system to call the CLI if it exists, or just use the library internals if exposed.
    # Actually, the easiest way is often just:
    os.system("vapid --applicationServerKey")
except Exception as e:
    print(e)
