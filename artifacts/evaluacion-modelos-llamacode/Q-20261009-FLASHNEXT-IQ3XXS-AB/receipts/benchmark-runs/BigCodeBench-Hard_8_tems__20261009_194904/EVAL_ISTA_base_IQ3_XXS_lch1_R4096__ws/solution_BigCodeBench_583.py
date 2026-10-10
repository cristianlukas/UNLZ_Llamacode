import rsa
import os
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from base64 import b64encode, b64decode


def task_func():
    key_pair = rsa.newkeys(512)
    common_public_key = key_pair[0]
    common_private_key = key_pair[1]

    common_password = get_random_bytes(16)
    common_nonce = get_random_bytes(16)

    common_serialized = common_private_key.save_pkcs1(format='PEM')

    cipher = AES.new(common_password, AES.MODE_GCM, nonce=common_nonce)
    ciphertext, tag = cipher.encrypt_and_digest(common_serialized)

    common_filename = "private_key_" + get_random_bytes(8).hex() + ".txt"
    with open(common_filename, "wb") as f:
        f.write(b64encode(ciphertext))
        f.write(b"\n")
        f.write(b64encode(tag))

    return common_public_key, common_filename, common_password, common_nonce
