"""Luxart extraction; retains labels and infers dimension order from image proportions."""
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

BASE = 'https://luxart.com'
SIZE = re.compile(r'(\d+(?:[.,]\d+)?)\s*[x×х]\s*(\d+(?:[.,]\d+)?)\s*cm', re.I)

class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []
    def text(self):
        return ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)
    def all(self):
        yield self
        for c in self.children:
            if isinstance(c, Node): yield from c.all()
    def has(self, token): return token in self.attrs.get('class','').split()

class Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.current)
        self.current.children.append(n)
        if tag not in {'img','input','meta','link','br','hr','source','area','base','embed','wbr','param','col'}:
            self.current = n
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs); self.handle_endtag(tag)
    def handle_endtag(self, tag):
        n = self.current
        while n.parent:
            if n.tag == tag:
                self.current = n.parent
                return
            n = n.parent
    def handle_data(self, data): self.current.children.append(data)

def parse_sizes(text):
    result=[]
    for a,b in SIZE.findall(text):
        pair=[float(a.replace(',','.')),float(b.replace(',','.'))]
        if pair not in result: result.append(pair)
    return result

def discover(html):
    products, pages = set(), set()
    for n in Tree(html).root.all():
        href = n.attrs.get('href','')
        u = urlparse(urljoin(BASE,href))
        if u.hostname not in {'luxart.com','www.luxart.com'}: continue
        url = BASE + u.path
        if re.fullmatch(r'/paveikslai/[^/]+/', u.path): products.add(url)
        elif re.fullmatch(r'/paveikslai/page/\d+/',u.path): pages.add(url)
    return {'products':sorted(products),'pages':sorted(pages)}

def parse_product(html, url):
    nodes=list(Tree(html).root.all())
    title=next((n.text().strip() for n in nodes if n.tag=='h1'),'')
    summary=next((n for n in nodes if n.has('summary')),None)
    # Only the current product: related products and global filters must never contribute sizes.
    scope=list(summary.all()) if summary else []
    if not summary:
        main=next((n for n in nodes if n.has('product') and n.tag!='li'),None)
        if main:
            scope=[n for n in main.all() if not any_ancestor(n, {'related','upsells','products'})]
    artist=next((n.text().strip() for n in scope if n.tag=='h3'),'')
    breadcrumb=next((n.text() for n in scope if n.has('woocommerce-breadcrumb')),'')
    category=breadcrumb.split('/')[-1].strip()
    is_artwork=not any(s in breadcrumb.casefold() for s in ['aksesuarai','dovanų kupon','dovanų ček'])
    options=[]
    for n in scope:
        if n.tag in {'label','option'} and SIZE.search(n.text()): options.append(n.text().strip())
    text=' '.join(options) if options else ' '.join(c for n in scope for c in n.children if isinstance(c,str))
    sizes=parse_sizes(text)
    image=next((n.attrs.get('content','') for n in nodes if n.tag=='meta' and n.attrs.get('property')=='og:image'),'')
    gallery=next((n for n in nodes if n.has('woocommerce-product-gallery')),None)
    size_order='square' if sizes and all(a==b for a,b in sizes) else 'unknown'
    if gallery:
        image=next((n.attrs.get('data-large_image') or n.attrs.get('data-src') or n.attrs.get('src') for n in gallery.all() if n.tag=='img'),image)
        artwork=next((n for n in gallery.all() if n.tag=='img' and 'data-large_image_width' in n.attrs),None)
        if artwork and size_order!='square':
            try:
                ratio=float(artwork.attrs['data-large_image_width'])/float(artwork.attrs['data-large_image_height'])
                orders=set()
                for a,b in sizes:
                    if a==b: continue
                    wh,hw=abs((a/b)/ratio-1),abs((b/a)/ratio-1)
                    orders.add(('wh' if wh<hw else 'hw') if min(wh,hw)<=0.15 and abs(wh-hw)>=0.15 else 'unknown')
                if len(orders)==1: size_order=orders.pop()
            except (KeyError,ValueError,ZeroDivisionError): pass
    variants=[]
    for pair in sizes:
        label=next((s for s in options if pair in parse_sizes(s)),f'{pair[0]:g} × {pair[1]:g} cm')
        prices=[float(p.replace(',','.')) for p in re.findall(r'€\s*(\d+(?:[.,]\d+)?)',label)]
        variants.append({'size':pair,'label':label,'price':prices[-1] if prices else None})
    return {'url':url,'title':title,'artist':artist,'image':urljoin(BASE,image) if image else '', 'sizes':sizes,'variants':variants,'size_order':size_order,'category':category,'is_artwork':is_artwork}

def any_ancestor(node, classes):
    n=node
    while n:
        if any(n.has(c) for c in classes): return True
        n=n.parent
    return False
