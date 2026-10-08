"""A module/package for obtaining physical data, mainly materials properties.
(Physical constants are provided by scipy.constants.) It contains:
    refindinf: an interface to the refractiveindex.info database (stored locally). 

This needs to
be organised somehow so additional types of data can be added.

Last modified 26/11/2015.
"""
import math
from math import pi
import scipy.constants as constants
constant=constants.physical_constants

SI={'c':constants.c,'e':constants.e,'E_h':constant['Hartree energy'][0],
'a_0':constant['Bohr radius'][0],'E_au':constant['atomic unit of electric field'][0],
'Z_vac':constant['characteristic impedance of vacuum'][0],'t_au':constant['atomic unit of time'][0],
'hbar':constants.hbar,'P_atm':1.01325e5,'ideal_gas_density_STP':2.6882e25,
'r_e':2.8179402894e-15,'epsilon_0':8.854e-12,'amu':constant['atomic mass constant'][0],
'h':constants.h,'k':constants.k,'m_e':constants.m_e}

eV_per_au=SI['E_h']/SI['e']

IP_eVs={'Ar':15.760833074,'Kr':13.9936,'Ne':21.5674,'Xe':12.1317,'He':24.58820574,
        'benzene':9.25,'toluene':8.82,'bromobenzene':8.98,'chlorobenzene':9.07,
        'fluorobenzene':9.20,'m-xylene':8.56,'o-xylene':8.56,'p-xylene':8.45}
        
def IP(name,unit='eV'):
    r=IP_eVs[name]
    if unit=='eV':
        return r
    elif unit=='au':
        return r/constant['Hartree energy in eV'][0]
    elif unit=='J':
        return r*SI['e']

c2pi=SI['c']*2*math.pi
c2pi_nmpfs=c2pi*1e-6
eV_lambda=2*math.pi*SI['c']*SI['hbar']/SI['e']

outer_electron_nl=dict(He=(1,0),Ne=(2,1),Ar=(3,1),Kr=(4,1),Xe=(5,1))

def nonlinear_refractive_index(name):
    """Nonlinear refractive index in cm^2/TW. For gases, at STP.
    TODO: include wavelength dependence"""
    if name=='Ne':
        return 8e-9 # cm^2/TW
    elif name=='He':
        return 3e-9
    elif name=='Ar':
        return 1e-7
    else:
        raise ValueError('Unknown substance %s'%name)
