import unittest, pathlib
from unittest.mock import mock_open, patch
from solution_BigCodeBench_771 import task_func
class TestCases(unittest.TestCase):
    def setUp(self):
        self.directory="/mnt/data/test_data"; self.rows=[["column1","column2"],["value1","value2"]]
    def test_file_creation_and_content(self):
        with patch('os.listdir', return_value=['Shan-1.csv','Shannon-2.csv']):
            data='\r\n'.join([','.join(r) for r in self.rows])+'\r\n'
            with patch('builtins.open', mock_open(read_data=data)) as mf:
                res=task_func(self.directory); exp=['Shan.csv','Shannon.csv']
                self.assertListEqual(res,exp)
                for e in exp: mf.assert_any_call(pathlib.Path(self.directory)/e, "w")
                h=mf()
                for r in self.rows: h.write.assert_any_call(','.join(r)+'\r\n')
    def test_empty_directory(self):
        with patch('os.listdir', return_value=[]): self.assertEqual(task_func(self.directory),[])
    def test_non_matching_files(self):
        with patch('os.listdir', return_value=['random.txt','test-123.txt']): self.assertEqual(task_func(self.directory),[])
    def test_mixed_file_types(self):
        with patch('os.listdir', return_value=['Shan-1.csv','test.txt','Shannon-2.pdf']):
            data='\r\n'.join([','.join(r) for r in self.rows])+'\r\n'
            with patch('builtins.open', mock_open(read_data=data)) as mf:
                self.assertEqual(task_func(self.directory),['Shan.csv'])
                mf.assert_any_call(pathlib.Path(self.directory)/'Shan-1.csv','r')
    def test_exception_handling(self):
        with patch('os.listdir', return_value=['Shan-1.csv']), patch('builtins.open', side_effect=IOError("x")):
            with self.assertRaises(IOError): task_func(self.directory)
import sys
def check(candidate):
    globals()['task_func']=candidate
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]); r=unittest.TestResult(); suite.run(r)
    if not r.wasSuccessful(): raise AssertionError(' | '.join(str(e) for _,e in r.failures+r.errors))
check(task_func); print('771 OK')
