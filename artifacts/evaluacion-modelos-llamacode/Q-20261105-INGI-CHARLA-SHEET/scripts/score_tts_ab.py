import re,sys,unicodedata
U=["cero","uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve","diez","once","doce","trece","catorce","quince","dieciséis","diecisiete","dieciocho","diecinueve","veinte","veintiuno","veintidós","veintitrés","veinticuatro","veinticinco","veintiséis","veintisiete","veintiocho","veintinueve"]
T=["","","","treinta","cuarenta","cincuenta","sesenta","setenta","ochenta","noventa"]
H=["","ciento","doscientos","trescientos","cuatrocientos","quinientos","seiscientos","setecientos","ochocientos","novecientos"]
def u1000(n):
    if n==100: return "cien"
    h,r=divmod(n,100); o=[H[h]] if h else []
    if r: o.append(U[r] if r<30 else T[r//10]+("" if r%10==0 else " y "+U[r%10]))
    return " ".join(o)
def w(n):
    if n==0: return "cero"
    m,rest=divmod(n,1000000); th,r=divmod(rest,1000); o=[]
    if m: o.append("un millón" if m==1 else w(m)+" millones")
    if th: o.append("mil" if th==1 else u1000(th)+" mil")
    if r: o.append(u1000(r))
    return " ".join(o)
def num(m):
    s=m.group(0); ip,_,dec=s.replace(".","").partition(",")
    out=w(int(ip))
    if dec: out+=" coma "+(w(int(dec)) if len(dec)<=2 and not dec.startswith("0") else " ".join(U[int(c)] for c in dec))
    return out
def norm(t):
    t=t.lower().replace("%"," por ciento")
    t=re.sub(r"\d[\d.]*(?:,\d+)?",num,t)
    t=re.sub(r"\b(veinti|)uno\b",r"\1un",t); t=t.replace("veintiun","veintiún")
    t=re.sub(r"\bun\b","uno",t); t=t.replace("veintiún","veintiuno")
    t="".join(c for c in unicodedata.normalize("NFD",t) if unicodedata.category(c)!="Mn")
    return re.sub(r"[^a-z0-9ñ ]"," ",t).split()
def ed(a,b):
    d=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        p,d[0]=d[0],i
        for j,y in enumerate(b,1): p,d[j]=d[j],min(d[j]+1,d[j-1]+1,p+(x!=y))
    return d[-1]
refs=[l.split("\t")[1] for l in open("corpus.tsv",encoding="utf-8").read().splitlines()]
for arm in sys.argv[1:]:
    hyps=open(arm,encoding="utf-8").read().splitlines()
    E=N=0; bad=0
    for r,h in zip(refs,hyps):
        rr,hh=norm(r),norm(h); e=ed(rr,hh); E+=e; N+=len(rr); bad+= e>0
    print(f"{arm}: WER {100*E/N:.1f}% ({E}/{N}), frases con error {bad}/20")
