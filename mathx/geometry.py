import math
import numpy as np
from scipy.ndimage.interpolation import map_coordinates
from . import uniformly_spaced_vector as usv
from . import *

def polar_to_cart(r,theta,phi):
    """Convert from polar to cartesian coordinate system.
    
    Angles in radians.
    
    Args:
        r: distance from origin
        theta: angle to z axis
        phi: angle around z axis, starting from x moving towards y
    
    Returns:
        tuple: x,y,z coordinates
    """
    rs=r*np.sin(theta)
    return rs*np.cos(phi),rs*np.sin(phi),r*np.cos(theta)
    
def polar_reg_grid_to_rect(r,theta,data,theta_repeats=False,osamp=1):
    """data dimensions are r, theta. r, theta must be (1D) sequences. If theta_repeats then
    an additional theta column is added, equal to the first. This is useful
    if theta runs from e.g. 0, Delta, ..., 2*pi-Delta"""
    max_r=r[-1]
    x=np.linspace(-max_r,max_r,len(r)*2*osamp)
    y=x[:,None]
    rxy=(x**2+y**2)**0.5
    thetaxy=np.arctan2(y,x)
    ri=usv.get_frac_ind(r,rxy)
    if theta_repeats:
        theta=np.r_[theta,theta[0]+2*math.pi*np.sign(theta[1]-theta[0])]#theta[-1]-theta[-2]]
        data=np.c_[data,data[:,0]]
    theta0=min(theta)
    thetai=usv.get_frac_ind(theta,(thetaxy-theta0)%(2*math.pi)+theta0)
    datayx=map_coordinates(data,np.stack((ri,thetai),-3))
    return x,y,datayx

def cart_to_polar(x,y,z,r_sign=1):
    """Convert from cartesian to polar coordinates.
    
    See polar_to_cart for defintions.
    """
    r=r_sign*(x**2+y**2+z**2)**0.5
    theta=np.arccos(mathx.divide0(z,r,1))
    phi=np.arctan2(y*r_sign,x*r_sign)
    return r,theta,phi
    
def polar_grid(Ntheta,Nphi,dim_theta=-2,dim_phi=-1):
    theta=math.pi*(reshape_vec(np.arange(Ntheta),dim_theta)+1)/(Ntheta+1)
    phi=math.pi*2*reshape_vec(np.arange(Nphi),dim_phi)/Nphi
    return theta,phi
    
def polar_perm_cart(theta,phi,perm):
    xs=polar_to_cart(1,theta,phi)
    xs=[xs[comp] for comp in perm]
    return cart_to_polar(*xs)[1:]
    
def negate_polar(theta,phi):
    return math.pi-theta,wrap_pm(phi+math.pi,math.pi)
