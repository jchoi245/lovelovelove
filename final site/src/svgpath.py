import re, numpy as np
def subpaths(d, ox=0, oy=0, n=12):
    toks = re.findall(r'[MCLHVZmclhvz]|-?[0-9.]+(?:e-?\d+)?', d)
    out, cur, pos, i, cmd = [], [], (0,0), 0, None
    def num():
        nonlocal i; v=float(toks[i]); i+=1; return v
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t): cmd=t; i+=1
        if cmd=='M':
            if cur: out.append(np.array(cur))
            pos=(num(),num()); cur=[pos]; cmd='L'
        elif cmd=='L': pos=(num(),num()); cur.append(pos)
        elif cmd=='H': pos=(num(),pos[1]); cur.append(pos)
        elif cmd=='V': pos=(pos[0],num()); cur.append(pos)
        elif cmd=='C':
            p0=np.array(pos); p1=np.array((num(),num())); p2=np.array((num(),num())); p3=np.array((num(),num()))
            for t_ in np.linspace(0,1,n)[1:]:
                cur.append(tuple((1-t_)**3*p0+3*(1-t_)**2*t_*p1+3*(1-t_)*t_**2*p2+t_**3*p3))
            pos=tuple(p3)
        elif cmd in 'Zz':
            if cur: out.append(np.array(cur)); cur=[]
            cmd=None
        else: raise ValueError(cmd)
    if cur: out.append(np.array(cur))
    return [p+np.array([ox,oy]) for p in out]
