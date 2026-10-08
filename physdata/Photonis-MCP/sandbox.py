import numpy as np
with open('CsI.txt','r') as f:
    f.readline() # header
    lines=f.readlines()

angstrom,log10_percent=np.array([[float(word.strip()) for word in line.split(',')] for line in lines]).T
