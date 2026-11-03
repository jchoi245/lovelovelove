import re, sys
IMG = {'imgRectangle':'assets/foot.png','imgRectangle1':'assets/foot1.png','imgRectangle2':'assets/foot2.png',
       'imgRectangle3':'assets/foot3.png','img34':'assets/src34.png','imgSample4':'assets/srcs4.png'}
FONT = {"Lemonada:SemiBold":"Lemonada","Lexend_Mega:Light":"Lexend_Mega","Epunda_Sans:Medium":"Epunda_Sans",
        "Epunda_Sans:Regular":"Epunda_Sans","Epunda_Sans:Italic":"Epunda_Sans"}
def conv(s):
    s = s.replace('className=', 'class=')
    s = re.sub(r'src=\{(\w+)\}', lambda m: 'src="%s"' % IMG.get(m.group(1), 'MISSING_'+m.group(1)), s)
    s = s.replace('style={{ containerType: "size" }}', 'style="container-type:size"')
    s = re.sub(r"font-\['([^']+)'\]", lambda m: "font-['%s']" % FONT.get(m.group(1), m.group(1).split(':')[0]), s)
    s = re.sub(r'<div([^>]*?)\s*/>', r'<div\1></div>', s)
    s = re.sub(r'\{`([^`]*)`\}', r'\1', s)
    s = s.replace(' aria-hidden ', ' aria-hidden="true" ')
    return s
def blocks(path):
    L = open(path).read().split('\n')
    out = {}; cur=None; buf=[]
    for l in L:
        m = re.match(r'^      <(div|p)\b', l)
        if m:
            if cur: out[cur] = '\n'.join(buf)
            nid = re.search(r'data-node-id="([^"]+)"', l)
            cur = nid.group(1) if nid else None; buf=[l]
        elif re.match(r'^    </div>', l) and cur:
            out[cur] = '\n'.join(buf); cur=None
        elif cur: buf.append(l)
    return out
