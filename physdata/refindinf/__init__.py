"""Functions for accessing the refractiveindex.info database."""
import os
import yaml
import numpy as np
import mathx

db_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),'database')
db_path=os.path.join(db_dir,'library.yml')
lib=yaml.load(open(db_path,'r'))

def print_lib():
    """Print all pages in the library in hierachical format."""
    for shelf in lib:
        print(shelf['name'])
        for book in shelf['content']:
            if not book.has_key('BOOK'):
                continue
            print('  '+book['BOOK'])
            for page in book['content']:
                if not page.has_key('PAGE'):
                    continue
                print('    '+page['PAGE'])
               
def lookup_shelves(shelf_str=None):
    # Pick shelves
    if shelf_str==None:
        shelves=lib
    else:
        shelves=filter(lambda shelf : shelf_str in shelf['name'] or shelf_str in shelf['SHELF'],lib)
        if len(shelves)==0:
            raise ValueError('No shelf matches '+shelf_str+' in library')
    return shelves
    
def lookup_books(book_str,shelves=lookup_shelves()):
    # Pick books
    def match_book(book):
        if not 'BOOK' in book:
            return False
        return book_str==book['BOOK']# or book_str in book['name']
    books=[]
    for shelf in shelves:
        books.extend(filter(match_book,shelf['content']))
    if len(books)==0:
        raise ValueError('No book matches '+book_str)
    return books    
    
def lookup_page(page_str,books):
    # Pick pages
    pages=[]
    for book in books:
        if page_str==None:
            pages.append(book['content'][0])
        else:
            pages.extend(filter(lambda page:page_str==page.get('PAGE'),book['content']))
    #search_desc='shelf %s, book %s, page %s'%(str(shelf_str),str(book_str),str(page_str))
    if len(pages)==0:
        raise ValueError('No matches for '+page_str)
    elif len(pages)>1:
        raise ValueError('More than one match for '+page_str)
    page=pages[0]
    return page
    
def load_page(page):
    file=open(os.path.join(db_dir,page['path']),'r')
    string=''
    for line in file:
        string=string+line.replace('\t','')
    ref=yaml.load(string)
    return ref 
    
class TabNKEntry:
    """Tabulated (n,k) refractiveindex.info database entry."""
    def __init__(self,ref,check_range=True):
        data=[]
        for line in ref['data'].split('\n'):
            try:
                data.append([float(x) for x in line.split(' ')])
            except ValueError as e:
                pass
        data=np.array(data)
        self._lamb=data[:,0]*1e-6
        self._n=data[:,1]
        self._k=data[:,2]
        self.check_range=check_range
        self.range=[self._lamb.min()*1e6, self._lamb.max()*1e6]
    def n(self,lamb):
        # interp gives error if passed complex valued yp, so must split up
        # real and imaginary parts
        return np.interp(lamb,self._lamb,self._n)+1j*np.interp(lamb,self._lamb,self._k)
    def __call__(self,lamb,check_range=None):
        check_range=(check_range if check_range is not None else self.check_range)
        lamb=np.array(lamb)
        mum=lamb*1e6
        if check_range and not mathx.geale(mum,*self.range).all():
            raise ValueError('Out of range ({0}--{1} micron). Pass check_range=False to ignore.'.format(*self.range))
        return self.n(lamb)

class FormulaEntry:
    """Dispersion formulae - see database/doc/Dispersion formulas.pdf"""    
    def __init__(self,ref,check_range=True):
        self.form_num=float(ref['type'][7:])
        self.c=np.array([float(x) for x in ref['coefficients'].split(' ')])
        self.range=[float(x) for x in ref['range'].split(' ')]
        self.check_range=check_range
    def __call__(self,lamb,check_range=None):
        check_range=(check_range if check_range is not None else self.check_range)
        lamb=np.array(lamb)
        mum=lamb*1e6
        if check_range and not mathx.geale(mum,*self.range).all():
            raise ValueError('Out of range ({0}--{1} micron). Pass check_range=False to ignore.'.format(*self.range))
        if self.form_num==1:
            # Sellmeier
            ns=1+self.c[0]
            mum2=mum**2
            for a,b in zip(self.c[1::2],self.c[2::2]):
                ns+=a*mum2/(mum2-b**2)
            n=ns**0.5
        elif self.form_num==2:
            ns=1+self.c[0]
            mum2=mum**2
            for a,b in zip(self.c[1::2],self.c[2::2]):
                ns+=a*mum2/(mum2-b)
            n=ns**0.5
        elif self.form_num==4:
            mum2=mum**2
            ns=self.c[0]
            for a,b,c,d in self.c[1:9].reshape((2,4)):
                ns+=a*mum**b/(mum2-c**d)
            for a,b in self.c[9:].reshape((-1,2)):
                ns+=a*mum**b
            n=ns**0.5
        elif self.form_num==6:
            # gases
            n=1+self.c[0]
            for a,b in zip(self.c[1::2],self.c[2::2]):
                n+=a/(b-mum**-2)
        else:
            raise ValueError('Unknown formula number %d'%self.form_num)
        return n
            
def parse_entry(ref,check_range=True):
    """Parse a yaml dictionary representing an entry, returning an
    entry object."""
    ref=ref['DATA'][0]
    type=ref['type']
    if type=='tabulated nk':
        return TabNKEntry(ref,check_range)
    elif type[0:7]=='formula':
        return FormulaEntry(ref,check_range)
    else:
        raise ValueError('Unknown type '+type)
        
def lookup_ref(book_str,page_str=None,shelf_str=None):
    """Look up entry in refractiveindex.info database."""
    shelves=lookup_shelves(shelf_str)
    books=lookup_books(book_str,shelves)
    page=lookup_page(page_str,books)
    return load_page(page)
      
def lookup_fun(book_str,page_str=None,shelf_str=None,check_range=True):
    ref=lookup_ref(book_str,page_str,shelf_str)
    return parse_entry(ref,check_range)
    
