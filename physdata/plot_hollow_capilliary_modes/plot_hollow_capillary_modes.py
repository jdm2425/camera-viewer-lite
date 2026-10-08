import numpy as np
from physdata import hollow_capillary as hc
import matplotlib.pyplot as plt
from matplotlib import animation


lamb=1.8e-6
radius=50e-6
num_points=50
x=np.linspace(-1,1,num_points)*radius
y=np.linspace(-1,1,num_points)[:,None]*radius
r=(x**2+y**2)**0.5
theta=np.arctan2(x,y)
dA=(x[1]-x[0])*(y[1,0]-y[0,0])
##
Er,Et,Ez,Hr,Ht,Hz=hc.calc_mode(1.5,radius,-1,1,lamb,r,theta,dA,0)
Ex,Ey=hc.cylindrical_to_cartesian(r,theta,Et,Er)
Hx,Hy=hc.cylindrical_to_cartesian(r,theta,Ht,Hr)
fig, ax = plt.subplots(1,1)
quiver=ax.quiver(x*1e6,y*1e6,Ex.real,Ey.real)

def update_quiver(num):
    num_cycle=10
    phi=(num/num_cycle)*2*np.pi
    Exp=(Ex*np.exp(1j*phi)).real
    Eyp=(Ey*np.exp(1j*phi)).real
    quiver.set_UVC(Exp,Eyp)

    return quiver

# you need to set blit=False, or the first set of arrows never gets
# cleared on subsequent frames
anim = animation.FuncAnimation(fig, update_quiver,interval=100, blit=False)

plt.show()
