import csv, importlib.util, io, sys
from pathlib import Path
from decimal import Decimal

def load(root):
    spec=importlib.util.spec_from_file_location('solution_ledger',Path(root)/'solution_ledger_fixed.py')
    if spec is None: raise AssertionError('missing solution_ledger_fixed.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def run(root, test):
    m=load(root)
    if test=='money':
        assert m.parse_amount('$1,234.50')==Decimal('1234.50')
        assert m.parse_amount('-3.455')==Decimal('-3.46')
        for v in ('','$1,2x','--2','1.234.567'):
            try: m.parse_amount(v)
            except (ValueError, TypeError): pass
            else: raise AssertionError(f'accepted invalid amount {v!r}')
    elif test=='validation':
        l=m.Ledger()
        e=l.add('2026-02-28','  Book shop ','12.5','  Office ', 'tax')
        assert e.amount==Decimal('12.50') and e.payee=='Book shop' and e.category=='office'
        for args in [('2026-02-30','x','1','a'),('2026-01-01',' ','1','a'),('2026-01-01','x','1',' ')]:
            try: l.add(*args)
            except (ValueError, TypeError): pass
            else: raise AssertionError(f'accepted invalid entry {args!r}')
    elif test=='balance_summary':
        l=m.Ledger(); l.add('2026-01-01','salary','2500','Income'); l.add('2026-01-02','rent','-900','Housing'); l.add('2026-01-03','food','-20.50','Food')
        assert l.balance()==Decimal('1579.50')
        s=l.summary()
        assert s['income']==Decimal('2500.00') and s['expenses']==Decimal('920.50') and s['balance']==Decimal('1579.50') and s['count']==3
        assert s['by_category']['housing']==Decimal('-900.00')
    elif test=='filters':
        l=m.Ledger(); a=l.add('2026-01-02','Corner Market','-25','Food'); l.add('2026-01-03','Book Store','-10','Books'); l.add('2026-02-01','market refund','5','Food')
        got=l.filter_entries(category=' FOOD ',start='2026-01-01',end='2026-01-31',query='market')
        assert [x.id for x in got]==[a.id]
    elif test=='undo':
        l=m.Ledger(); a=l.add('2026-01-01','x','10','a'); b=l.add('2026-01-02','y','-2','b')
        assert l.undo() is True and [x.id for x in l.entries()]==[a.id] and l.balance()==Decimal('10.00')
        assert l.undo() is True and l.entries()==[] and l.balance()==Decimal('0.00')
        assert l.undo() is False
    elif test=='csv':
        l=m.Ledger(); l.add('2026-01-01','Cafe, Central','-12.34','Food','said "hello"'); l.add('2026-01-02','Pay','100','Income')
        raw=l.to_csv(); restored=m.Ledger.from_csv(raw)
        assert [(e.date,e.payee,e.amount,e.category,e.note) for e in restored.entries()]==[(e.date,e.payee,e.amount,e.category,e.note) for e in l.entries()]
    elif test=='ids':
        l=m.Ledger(); first=l.add('2026-01-01','a','1','x'); restored=m.Ledger.from_csv(l.to_csv()); second=restored.add('2026-01-02','b','2','x')
        assert second.id>first.id
    elif test=='stable_order':
        l=m.Ledger(); a=l.add('2026-01-02','later','1','x'); b=l.add('2026-01-01','earlier','1','x')
        assert [e.id for e in l.entries()]==[a.id,b.id]
        assert [e.id for e in l.filter_entries(start='2026-01-01',end='2026-01-02')]==[a.id,b.id]
    else: raise AssertionError('unknown test '+test)
    print('PASS: '+test)

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: ledger_grader.py WORKSPACE TEST')
    run(sys.argv[1],sys.argv[2])
