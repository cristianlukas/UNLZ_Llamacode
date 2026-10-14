import unittest, os, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from solution_BigCodeBench_360 import task_func
def create_dummy_excel(file_path='test.xlsx'):
    pd.DataFrame({'A':[10,30],'B':[20,40]}).to_excel(file_path, index=False, sheet_name='TestSheet')
def extract_means_from_fig(fig):
    ax=fig.get_axes()[0]
    bars=[r for r in ax.get_children() if isinstance(r, matplotlib.patches.Rectangle)]
    return [b.get_height() for b in bars[:-1]]
class TestCases(unittest.TestCase):
    def setUp(self): create_dummy_excel()
    def tearDown(self): os.remove('test.xlsx')
    def test_normal_functionality(self):
        res,fig=task_func('test.xlsx','TestSheet')
        self.assertIsInstance(res,dict); self.assertIsInstance(fig,plt.Figure)
        self.assertEqual(fig.axes[0].get_title(),'Mean and Standard Deviation')
    def test_non_existent_file(self):
        with self.assertRaises(FileNotFoundError): task_func('non_existent.xlsx','Sheet1')
    def test_invalid_sheet_name(self):
        with self.assertRaises(ValueError): task_func('test.xlsx','NonExistentSheet')
    def test_correct_mean_and_std_values(self):
        res,_=task_func('test.xlsx','TestSheet')
        self.assertEqual(res, {'A':{'mean':20.0,'std':10.0},'B':{'mean':30.0,'std':10.0}})
    def test_bar_chart_labels(self):
        _,fig=task_func('test.xlsx','TestSheet')
        ax=fig.axes[0]; self.assertEqual(ax.get_xlabel(),'Columns'); self.assertEqual(ax.get_ylabel(),'Values')
    def test_value(self):
        res,fig=task_func('test.xlsx','TestSheet')
        self.assertEqual({'A':{'mean':20.0,'std':10.0},'B':{'mean':30.0,'std':10.0}}, res)
        self.assertEqual(extract_means_from_fig(fig), [20,30])
import sys
def check(candidate):
    globals()['task_func']=candidate
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]); r=unittest.TestResult(); suite.run(r)
    if not r.wasSuccessful(): raise AssertionError(' | '.join(str(e) for _,e in r.failures+r.errors))
check(task_func); print('360 OK')
