import os, shutil, unittest
from solution_BigCodeBench_765 import task_func
class TestCases(unittest.TestCase):
    def setUp(self):
        self.test_dir='test_dir'; self.target_dir='target_dir'
        os.makedirs(self.test_dir, exist_ok=True); os.makedirs(self.target_dir, exist_ok=True)
    def tearDown(self):
        shutil.rmtree(self.test_dir); shutil.rmtree(self.target_dir)
    def test_files_with_content(self):
        tf={'file1.txt':'Hello','file2.txt':'World'}
        for f,c in tf.items(): open(os.path.join(self.test_dir,f),'w').write(c)
        fp={os.path.join(self.test_dir,k):v for k,v in tf.items()}
        cf=task_func(fp,self.target_dir); self.assertEqual(len(cf),2)
        for c in cf:
            self.assertTrue(os.path.isfile(c)); self.assertTrue(c.startswith(self.target_dir))
    def test_files_with_no_content(self):
        tf={'file1.txt':'Hello','file2.txt':None}
        for f,c in tf.items():
            with open(os.path.join(self.test_dir,f),'w') as fh:
                if c: fh.write(c)
        fp={os.path.join(self.test_dir,k):v for k,v in tf.items()}
        cf=task_func(fp,self.target_dir); self.assertEqual(len(cf),1)
        self.assertTrue(os.path.isfile(cf[0])); self.assertTrue(cf[0].startswith(self.target_dir))
    def test_files_do_not_exist(self):
        tf={'file1.txt':'Hello','file2.txt':'World'}
        fp={os.path.join(self.test_dir,k):v for k,v in tf.items()}
        self.assertEqual(len(task_func(fp,self.target_dir)),0)
    def test_mixed_case(self):
        tf={'file1.txt':'Hello','file2.txt':None,'file3.txt':'World'}
        for f,c in tf.items():
            with open(os.path.join(self.test_dir,f),'w') as fh:
                if c: fh.write(c)
        fp={os.path.join(self.test_dir,k):v for k,v in tf.items()}
        cf=task_func(fp,self.target_dir); self.assertEqual(len(cf),2)
        for c in cf:
            self.assertTrue(os.path.isfile(c)); self.assertTrue(c.startswith(self.target_dir))
    def test_empty_dict(self):
        self.assertEqual(len(task_func({},self.target_dir)),0)
import sys
def check(candidate):
    globals()['task_func']=candidate
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]); r=unittest.TestResult(); suite.run(r)
    if not r.wasSuccessful(): raise AssertionError(' | '.join(str(e) for _,e in r.failures+r.errors))
check(task_func); print('765 OK')
