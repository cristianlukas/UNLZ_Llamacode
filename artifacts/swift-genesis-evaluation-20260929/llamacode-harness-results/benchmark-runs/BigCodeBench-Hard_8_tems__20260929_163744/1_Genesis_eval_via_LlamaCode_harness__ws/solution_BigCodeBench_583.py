import rsa
import os
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from base64 import b64encode, b64decode

def task_func():
    pub, priv = rsa.newkeys(2048)
    password = get_random_bytes(16)
    nonce = get_random_bytes(16)
    key_bytes = priv.save_pkcs1()
    cipher = AES.new(password, AES.MODE_CTR, nonce=nonce)
    encrypted = cipher.encrypt(key_bytes)
    filename = "private_key_" + os.urandom(8).hex() + ".txt"
    with open(filename, "wb") as f:
        f.write(encrypted)
    return pub, filename, password, nonce
