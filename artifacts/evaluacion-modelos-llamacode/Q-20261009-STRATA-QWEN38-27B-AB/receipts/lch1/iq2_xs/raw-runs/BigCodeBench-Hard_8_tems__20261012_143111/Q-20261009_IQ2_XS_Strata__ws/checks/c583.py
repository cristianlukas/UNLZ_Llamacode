import unittest, os, rsa
from Crypto.Cipher import AES
from base64 import b64decode
from solution_BigCodeBench_583 import task_func
class TestCases(unittest.TestCase):
    filenames=[]
    def test_return_type(self):
        pub,f,_,_=task_func(); self.assertIsInstance(pub,rsa.PublicKey); self.assertIsInstance(f,str); self.filenames.append(f)
    def test_file_creation(self):
        _,f,_,_=task_func(); self.assertTrue(os.path.exists(f)); self.filenames.append(f)
    def test_file_content(self):
        _,f,_,_=task_func()
        self.assertTrue(open(f,'r').read()); self.filenames.append(f)
    def test_key_size(self):
        pub,f,_,_=task_func(); self.assertEqual(pub.n.bit_length(),512); self.filenames.append(f)
    def test_unique_file_per_call(self):
        _,f1,_,_=task_func(); _,f2,_,_=task_func(); self.assertNotEqual(f1,f2); self.filenames.extend([f1,f2])
    def test_encryption_decryption(self):
        pub,f,pw,nonce=task_func(); self.filenames.append(f)
        enc=b64decode(open(f,'r').read())
        cipher=AES.new(pw,AES.MODE_EAX,nonce=nonce)
        priv=rsa.PrivateKey.load_pkcs1(cipher.decrypt(enc)); self.assertIsInstance(priv,rsa.PrivateKey)
    def tearDown(self):
        for f in self.filenames:
            if os.path.exists(f): os.remove(f)
import sys
def check(candidate):
    globals()['task_func']=candidate
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]); r=unittest.TestResult(); suite.run(r)
    if not r.wasSuccessful(): raise AssertionError(' | '.join(str(e) for _,e in r.failures+r.errors))
check(task_func); print('583 OK')
