import rsa
import os
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from base64 import b64encode, b64decode
def task_func():
    (public_key, private_key) = rsa.newkeys(512)

    password = get_random_bytes(16)
    nonce = get_random_bytes(16)
    filename = "private_key_" + get_random_bytes(8).hex() + ".txt"

    private_pem = private_key.save_pkcs1()
    if isinstance(private_pem, str):
        private_pem = private_pem.encode('utf-8')

    cipher = AES.new(password, AES.MODE_EAX, nonce=nonce)
    encrypted = cipher.encrypt(private_pem)

    with open(filename, 'w') as f:
        f.write(b64encode(encrypted).decode('utf-8'))

    return public_key, filename, password, nonce
