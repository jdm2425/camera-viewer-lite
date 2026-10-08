import numpy as np
from collections import namedtuple
from scipy.special import jn_zeros,jn,jvp
from math import pi
from . import SI

cot=lambda theta:1/np.tan(theta)

def calc_mode(nu,a,n,m,lamb,r,theta,dA,theta0=0):
    """
    If n == 0, whether the mode is TE or TM is denoted by the sign of m. Positive m means TE.

    Marcatili, E. & Schmeltzer, R.,
    Hollow metallic and dielectric waveguides for long distance optical transmission and lasers
    (Long distance optical transmission in hollow dielectric and metal circular waveguides, examining normal mode propagation),
    Bell System Technical Journal, 1964, 43, 1783-1809

    Args:
        nu: refractive index?
        a: radius
        n:
        m:
        theta0:
        lamb:
        r:
        theta:
        dA:

    Returns:
        tuple of tuples (Er,Et,Ez),(Hr,Ht,Hz)
    """
    k=2*pi/lamb
    eff_ind=calc_eff_ind(nu,a,n,m,lamb)
    gamma=eff_ind*k
    u=jn_zeros(abs(n-1),abs(m))[-1]
    ki=(k**2-gamma**2)**0.5
    ke=(nu**2*k**2-gamma**2)**0.5
    r,theta=np.broadcast_arrays(r,theta)
    ri=r[r<=a]
    re=r[r>a]
    thetai=theta[r<=a]
    thetae=theta[r>a]
    # We calculate inner and outer regions sequentially, so pre-allocate field arrays.
    Er=np.zeros(r.shape,dtype=complex)
    Et=np.zeros(r.shape,dtype=complex)
    Ez=np.zeros(r.shape,dtype=complex)
    Hr=np.zeros(r.shape,dtype=complex)
    Ht=np.zeros(r.shape,dtype=complex)
    Hz=np.zeros(r.shape,dtype=complex)
    # Treat each mode type in turn.
    if n==0:
        # TE/TM mode.
        if m>0:
            # TE mode.
            # Inner region.
            Et[r<=a]=jn(1,ki*ri)
            Hr[r<=a]=-SI['Z_vac']**(-1)*jn(1,ki*ri)
            Hz[r<=a]=-1j*SI['Z_vac']**(-1)*u/(k*a)*jn(0,ki*ri)
            # Outer region
            of=1j*u/(k*(a*re*(nu**2-1))**0.5)*jn(0,u)*np.exp(1j*ke*(re-a))
            Et[r>a]=-1*of
            Hr[r>a]=SI['Z_vac']**(-1)*of
            Hz[r>a]=-1j*(nu**2-1)**0.5*SI['Z_vac']**(-1)*of
        else:
            # TM mode.
            # Inner region.
            Er[r<=a]=jn(1,ki*ri)
            Ez[r<=a]= 1j*u/(k*a)*jn(0, ki*ri)
            Ht[r<=a]= SI['Z_vac']**(-1)*jn(1,ki*ri)
            # Outer region.
            of = 1j*u*jn(0, u)/(k*(a*re*(nu**2 - 1))**0.5)*np.exp(1j*ke*(re-a))
            Er[r>a]=-1/nu**2*of
            Ez[r>a]=(nu**2 - 1)**0.5*of
            Ht[r>a]=-SI['Z_vac']**(-1)*of
    else:
        # HE mode.
        # Inner region.
        Et[r<=a]=(jn(n-1,ki*ri)+1j*u**2/(2*n*k*a)*(nu**2-1)**0.5*jvp(n,ki*ri))*np.cos(n*(thetai+theta0))
        Er[r<=a]=(jn(n-1,ki*ri)+1j*u/(2*k*ri)*(nu**2-1)**0.5*jn(n, ki*ri))*np.sin(n*(thetai+theta0))
        Ez[r<=a]=-1j*u/(k*a)*jn(n,ki*ri)*np.sin(n*(thetai+theta0))
        Ht[r<=a]=SI['Z_vac']**(-1)*Er[r<=a]
        Hr[r<=a]= -SI['Z_vac']**(-1)*Et[r<=a]
        Hz[r<=a]= -SI['Z_vac']**(-1)*Ez[r<=a]*cot(n*(thetai + theta0))
        # Outer region.
        of = 1j*u/(k*(a*re*(nu**2-1))**0.5)*jn(n,u)*np.exp(1j*ke*(re-a))
        Et[r>a]=np.cos(n*(thetae+theta0))*of
        Er[r>a]=np.sin(n*(thetae+theta0))*of
        Ez[r>a]=-(nu**2-1)**0.5*np.sin(n*(thetae + theta0))*of
        Ht[r>a]=nu**2*SI['Z_vac']**(-1)*Er[r>a]
        Hr[r>a]=-SI['Z_vac']**(-1)*Et[r>a]
        Hz[r>a]=-SI['Z_vac']**(-1)*Ez[r>a]*cot(n*(thetae+theta0))
    # Normalize
    nc=calc_mode_norm(Et,Er,Ht,Hr,dA)
    Er=Er/nc
    Et=Et/nc
    Ez=Ez/nc
    Hr=Hr/nc
    Ht=Ht/nc
    Hz=Hz/nc

    return CylindricalField(Er,Et,Ez,Hr,Ht,Hz)

def calc_mode_norm(Et,Er,Ht,Hr,dA):
    return (0.5*((Er*Ht.conj()-Et*Hr.conj())*dA).real.sum())**0.5

CylindricalField=namedtuple('Field',('Er','Et','Ez','Hr','Ht','Hz'))

def calc_mode_overlap(f1,f2,dA):
    return 1/4*((f1.Er*f2.Ht.conj()-f1.Et*f2.Hr.conj()+f2.Er.conj()*f1.Ht-f2.Et.conj()*f1.Hr)*dA).sum()

def cylindrical_to_cartesian(r,theta,Et,Er):
    Ex=-np.sin(theta)*Et+np.cos(theta)*Er
    Ey=np.cos(theta)*Et+np.sin(theta)*Er
    return Ex,Ey

def calc_eff_ind(nu,a,n,m,lamb):
    """Approximate effective index of hollow capillary
   
    Args:
        nu: refractive index of wall
        a: radius
        n: order, if 0 then TE (m>0) or TM (m<0)
        m: azimuthal order
        lamb: wavelength (SI)

    Taken from 
    Marcatili, E. & Schmeltzer, R., 
    Hollow metallic and dielectric waveguides for long distance optical transmission and lasers
    (Long distance optical transmission in hollow dielectric and metal circular waveguides, examining normal mode propagation),
    Bell System Technical Journal, 1964, 43, 1783-1809
    """
    # m-th root of J_{n-1}. Just below (1). Root of J_n is also root of J_{-n}
    u=np.vectorize(lambda n,m:jn_zeros(abs(n-1),abs(m))[-1])(n,m)
    def calc_nu_n(n,m,nu):
        if n==0:
            if m>0:
                return 1/(nu**2-1)**0.5
            elif m<0:
                return nu**2/(nu**2-1)**0.5
        else:
            return 0.5*(nu**2+1)/(nu**2-1)**0.5
    nu_n=np.vectorize(calc_nu_n,otypes=('complex',))(n,m,nu)
   
    delta=abs(n)==1
    # (21)
    beta=2*pi/lamb*(1-0.5*(u*lamb/(2*pi*a))**2*(1+np.imag(nu_n*lamb/(pi*a))))
    alpha=(u/(2*pi))**2*lamb**2/a**3*np.real(nu_n)
    gamma=beta+1j*alpha
    n=gamma*lamb/(2*pi)

    return n

def name(n,m):
    if hasattr(n,'__len__') or hasattr(m,'__len__'):
        return np.vectorize(name)(n,m)
    if n==0:
        if m>0:
            return 'TE0%d'%m
        elif m<0:
            return 'TM0%d'%(-m)
    else:
        return 'HE%d%d'%(n,m)
        
def fundamental_area(radius):
    """Effective area (ratio of power to peak intensity) of HCF fund. mode.
    
    See RT2 p75 for derivation."""
    C=np.pi*jn(1,2.405)**2
    return C*radius**2

#eff_ind(1.5,100e-6,1,1,800e-9)
