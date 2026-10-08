import numpy as np
from physdata import hollow_capillary as hc

def test_calc_mode():
    """Check orthogonality of modes numerically."""
    lamb=1.8e-6
    radius=50e-6
    num_points=50
    x=np.linspace(-1,1,num_points)*radius
    y=np.linspace(-1,1,num_points)[:,None]*radius
    r=(x**2+y**2)**0.5
    theta=np.arctan2(x,y)
    dA=(x[1]-x[0])*(y[1,0]-y[0,0])
    ##
    M=5
    N=3
    fields=[]
    for m in np.arange(1,M+1):
        for n in np.arange(-N,N+1):
            for theta0 in (0,np.pi/2):
                fields.append(hc.calc_mode(1.5,radius,m,n,lamb,r,theta,dA,theta0))
    rows=[]
    for f1 in fields:
        row=[]
        for f2 in fields:
            row.append(hc.calc_mode_overlap(f1,f2,dA))
        rows.append(row)
    overlap=np.array(rows)
