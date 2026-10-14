import rsa
import os
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from base64 import b64encode, b64decode

def task_func():
    public_key, private_key = rsa.newkeys(512)

    password = get_random_bytes(16)
    nonce = get_random_bytes(16)

    cipher = AES.new(password, AES.MODE_EAX, nonce=nonce)
    ciphertext = cipher.encrypt(private_key.save_pkcs1())

    filename = "private_key_" + get_random_bytes(8).hex() + ".txt"

    with open(filename, 'wb') as file:
        file.write(b64encode(ciphertext))

    return public_key, filename, password, nonce
