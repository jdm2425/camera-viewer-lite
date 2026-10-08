"""Thin standardization wrappers around the periodictable package.

From the point of view of my work, the periodictable package has a few
idiosynchrasies:
    g/cm^3 instead of SI
    gas density specified at liquids boiling temperature
"""
from physdata import SI
import periodictable

def mass_density(symbol):
    """Mass density in kg/m^3.
    
    Densities for solids are given at 20 degrees C (and presumably at 1 atm). The
    periodictable documentation:
    http://www.reflectometry.org/danse/docs/elements/api/density.html#module-periodictable.density
    doesn't say.
    Gases are assumed ideal at 20 degrees, 1 atm."""
    element=getattr(periodictable,symbol)
    if symbol in ('H','N','O','F','Cl','He','Ne','Ar','Kr','Xe'):
        # Need to correct from STP to 20 deg C
        return element.mass*SI['amu']*SI['ideal_gas_density_STP']*273/293    
    else:
        # convert from g/cm^2 to kg/m^3
        return element.density*1e3
        
def number_density(symbol):
    """Number density in particles/m^3."""
    element=getattr(periodictable,symbol)
    return mass_density(symbol)/(element.mass*SI['amu'])
    
