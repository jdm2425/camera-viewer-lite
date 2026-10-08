from physdata.refindinf import *

ref=load_page(lookup_page('Eimerl-o',lookup_books('BaB2O4')))
entry=parse_entry(ref)
assert(abs(entry(220e-9)-1.8284)<1e-3)
assert(abs(lookup_fun('SiO2')(800e-9)-1.4533)<1e-3)
