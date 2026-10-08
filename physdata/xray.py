import os
import numpy as np
from . import SI,periodic_table,eV_lambda
from periodictable import xsf
import pyqtgraph_extended as pg

def refractive_index(element,eV,mass_density=None):
    """Refractive index using periodictable package.
    
    Imaginary part is positive i.e. optics rather than x-ray convention.
    
    Args:
        mass_density (float or None): in kg/m^3. If not given, then :func:`physdata.periodic_table.mass_density`
        is used.
    """
    if mass_density is None:
        mass_density=periodic_table.mass_density(element)
    # xsf function accepts keV and g/cm^3
    n=xsf.index_of_refraction(compound=element,energy=eV/1e3,density=mass_density/1e3).conj()
    return n
    
def get_andor_ccd_qe(micron=15):
    """BI epi curve with given micron from Andor data."""
    with open(os.path.join(os.path.dirname(__file__),'Andor','BI_%.0fmicron_noAR.txt'%micron),'rt') as f:
        lines=f.readlines()[2:]
    eV,qe=np.array([[float(word.strip()) for word in line.split()] for line in lines]).T
    return eV,qe
    
def get_andor_ccd_response(micron=15):
    """
    Args:
        micron (int): the pixel size
    
    Returns:
        eV,counts_per_photon
    """
    eV,qe=get_andor_ccd_qe(micron)
    counts_per_photon=qe*eV/3.65
    return eV,counts_per_photon
        
    # eV=[10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,
    #     210,220,230,240,250,300,400,600,800,1200,1600,1700,1800,1900,2000,2200,2300,
    #     2500,2700,2800,2900,3000,3300,3600,3700,3800,3900,4000,4500,5000,5500,6000,
    #     6500,7000,7500,8000,8500,9000,9500,10000,12000,14000,16000,18000,20000,22000,
    #     24000,26000,28000,30000]
    #     
    # qe=np.asarray([2,19.04,68.87,73.65,78.64,82.08,83.67,88.29,89.67,70.98,30.25,
    #     15.33,13.97,15.61,15.76,16.13,15.91,18.83,28.79,33.06,37.26,41.55,46.95,
    #     52.79,59,65,75,89,95,95,97.99,96.61,94.56,97.12,97.45,97.98,98.19,98.53,
    #     98.8,98.91,99,99.08,99.21,99.06,98.91,98.7,98.4,98.03,94.69,88.95,81.47,
    #     73.19,64.89,57.06,49.96,43.68,38.19,33.45,29.36,25.85,16.04,10.49,7.19,
    #     5.13,3.78,2.87,2.23,1.78,1.45,1.2])/100
    
def interp_andor_ccd_response(eV):
    eV_samp,cpp_samp=get_andor_ccd_response()
    return np.interp(eV,eV_samp,cpp_samp)
    
def get_pixis_xo_400b_qe():
    """Quantum efficiency of Princeton Instruments PIXIS-XO: 400B.
    
    From data sheet: Princeton_Instruments_PIXIS_XO_400B_rev_N2_9_6_2012.pdf
    available at www.princetoninstruments.com/userfiles/files/assetLibrary/Datasheets
    
    TODO: high energy part of curve
    
    Returns:
        tuple of arrays: photon energy in eV and corresponding quantum efficiency
            as a fraction
    """
    with open(os.path.join(os.path.dirname(__file__),'Princeton_PIXIS_XO_400B','qe1-90eV.txt'),'r') as f:
        f.readline() # header
        lines=f.readlines()
    data=np.array([[float(word.strip()) for word in line.split(',')] for line in lines])
    eV,qe=data[data[:,0].argsort()].T
    return eV,qe/100

def get_pixis_xo_400b_response():
    eV,qe=get_pixis_xo_400b_qe()
    counts_per_photon=qe*eV/3.65
    return eV,counts_per_photon
    
def interp_pixis_xo_400b_response(eV):
    eV_samp,cpp_samp=get_pixis_xo_400b_response()
    return np.interp(eV,eV_samp,cpp_samp)

        
def get_poletto_2014_response(grating_lines_per_mm):
    """Response of spectrometer in Poletto et al. 2014.
    
    The spectrometer comprises a Hitachi grating
    and Princeton
    XUV CCD (PIXIS-XO 400B, 1340 × 400 pixel, 20-μm pixel size). The gratings
    are 1200 lines/mm (001-0437) or 2400 lines/mm (001-0450).
     Data was stolen
    from the red and black curves of Fig. 6 of 
    Poletto et al., Spectrometer for X-ray emission experiments at FERMI
    free-electron-laser Review of Scientific Instruments, 2014, 85.
    
    Args:
        grating_lines_per_mm: 1200 or 2400
    Returns:
        eV,counts_per_photon: vectors
    """
    if grating_lines_per_mm==1200:
        eV=np.array([  26.05213393,   36.2254633 ,   41.09096865,   49.05270469,
            58.78371539,   72.05327544,   85.3228355 ,   95.0538462 ,
            103.01558224,  107.88108759,  114.07354895,  122.47760365,
            133.53557036,  149.01672375,  168.0364265 ,  183.51757989])
        counts_per_photon=np.array([ 0.03736721,  0.08002615,  0.11651124,  0.16195376,  0.22980169,
            0.36141831,  0.59843153,  0.80240667,  0.95581892,  1.02194427,
            1.05398794,  1.02194427,  0.96074993,  0.85791868,  0.76216176,
            0.69832342])
    elif grating_lines_per_mm==2400:
        eV=np.array([ 165.66648125,  195.91785043,  218.60637731,  238.18079266,
            250.63723879,  266.65266953,  276.43987721,  297.79378486,
            323.1515502 ,  349.84393477,  379.65043087,  407.67743467,
            435.70443846,  459.72758457,  484.19560376,  514.44697293,
            545.14321519,  594.52412664,  632.78321118,  681.27437648,
            720.86808026,755.3356329 ,  799.15057553])
        counts_per_photon=np.array([ 0.10641604,  0.12623487,  0.14516627,  0.16607507,  0.18706832,
            0.22421661,  0.25518719,  0.3138807 ,  0.37816366,  0.45092018,
            0.53767464,  0.61830952,  0.70736679,  0.78045865,  0.83910616,
            0.93061442,  1.01095559,  1.13874867,  1.23705833,  1.33691819,
            1.42257954, 1.48437282,  1.57581718])
    return eV,counts_per_photon

def interp_poletto_2014_response(eV,grating_lines_per_mm):
    eV_samp,counts_per_photon_samp=get_poletto_2014_response(grating_lines_per_mm)
    counts_per_photon=np.interp(eV,eV_samp,counts_per_photon_samp)
    return counts_per_photon
    
def get_hitachi_grating_efficiency(lines_per_mm):
    """First-order efficiency of Hitachi flat field grating.
    Obtained by correcting Poletto 2014 measurement for spectral response of the
    CCD.
    
    Args:
        lines_per_mm (int): 1200 or 2400
    
    Returns:
        tuple: vector of eV and corresponding efficiency"""
    eV_samp,_=get_poletto_2014_response(lines_per_mm)
    # Sample more finely to capture variations in camera response
    eV=np.linspace(eV_samp[0],eV_samp[-1],100)
    total_cpp=interp_poletto_2014_response(eV,lines_per_mm)
    ccd_cpp=interp_pixis_xo_400b_response(eV)
    grating_efficiency=total_cpp/ccd_cpp
    return eV,grating_efficiency
    
def interp_hitachi_grating_efficiency(eV,lines_per_mm):
    eV_samp,eff_samp=get_hitachi_grating_efficiency(lines_per_mm)
    return np.interp(eV,eV_samp,eff_samp)
    
def get_photonis_mcp_efficiency(coating,smooth=True):
    """Efficiency of a Photonis MCP from their Powerpoint presentation.
    
    Args:
        coating (str): one of uncoated, CsI, MgF2
        smooth: whether to smooth MCP data (recommended - the rasterized plot data
            has unphysical jumps)
    
    Returns:
        tuple: vector of wavelength in nm and efficiency as a fraction
    """
    coatings='uncoated','CsI','MgF2'
    if coating not in coatings:
        raise ValueError('Coating must be one of %s'%', '.join(coatings))
    with open(os.path.join(os.path.dirname(__file__),'Photonis-MCP',coating+'.txt'),'r') as f:
        f.readline() # header
        lines=f.readlines()
    data=np.array([[float(word.strip()) for word in line.split(',')] for line in lines])
    data=data[data[:,0].argsort()[::-1]]
    angstrom,log10_percent=data.T
    from scipy.signal import savgol_filter
    if smooth:
        log10_percent=savgol_filter(log10_percent,33,3)
    eV=eV_lambda/(angstrom*1e-10)
    return eV,10**(log10_percent-2)
    
def interp_photonis_mcp_efficiency(eV,coating,smooth=True):
    """
    Args:
        eV: photon energy in eV, arbitrarily sampled
        smooth: whether to smooth MCP data (recommended - the rasterized plot data
            has unphysical jumps)
    """
    eV_samp,eff_samp=get_photonis_mcp_efficiency(coating,smooth)
    return np.interp(eV,eV_samp,eff_samp)
    
def interp_hitachi_photonis_efficiency(eV,lines_per_mm,coating,smooth_mcp=True):
    """Efficiency of spectrometer with Hitachi grating and Photonis MCP.
    
    (TODO per photon or per unit energy?) 
    
    Args:
        eV (numeric): photon energy in eV
        lines_per_mm (int): 1200 or 2400
        coating: uncoated, CsI or MgF2
        smooth_mcp: whether to smooth MCP data (recommended)
        
    Returns:
        numeric: the efficiency
    """
    grating=interp_hitachi_grating_efficiency(eV,lines_per_mm)
    mcp=interp_photonis_mcp_efficiency(eV,coating,smooth_mcp)
    return grating*mcp
    
def plot_hitachi_1200lpmm_efficiency(gl=None):
    """Plot measurements of Hitachi 1200/mm flat field grating efficiency.
    
    The papers are:
    Poletto et al. Spectrometer for X-ray emission experiments at FERMI free-electron-laser Review of Scientific Instruments, 2014, 85
    Hage, A. Development of an XUV Spectrometer for diagnostics of high harmonic radiation pulses generated in a gas jet array. Universit¨at Hamburg, 2012
    Frassetto et al. Compact spectrometer for the analysis of high harmonics content of extreme-ultraviolet free-electron-laser radiation Proc. SPIE, 2010, 7802, 780209-780209-8
    Edelstein et al. Extreme UV measurements of a varied line-space Hitachi reflection grating: efficiency and scattering Appl. Opt., OSA, 1984, 23, 3267_1-3270
    
    David Neely is personal comms to Dane Austin, Jan 2017
    
    Not all data points in the papers are given - I wrote this function for the benzenes experiment, which only goes up to 40 eV.
    
    Returns:
        If gl is given, returns an :class:`.AlignedPlotItem`. If gl is not given,
            returns tuple of the created GraphicsLayoutWidget and the plot.
    """
    def plot_gl(gl):
        eV,eff=get_hitachi_grating_efficiency(1200)
        plot=gl.addAlignedPlot(title='Hitachi 1200/mm flat field grating efficiency at 3&deg;',labels={'left':'efficiency (%)','bottom':'photon energy (eV)'})
        pg.addLegend(plot,offset=(-1,1),background_color='00000000',vertical_spacing=0,margins=(0,0,0,0))#,border_color='00000000')
        plot.plot(eV,eff*100,pen='b',name='Poletto 2014')
        data=(21,5),(25,6),(31,8),(40,11)
        plot.plot(*zip(*data),pen=None,symbol='o',symbolBrush='r',name='Hage 2012')
        data=(25,5),(31,5.3),(36,8.3),(40,10.5)
        plot.plot(*zip(*data),pen=None,symbol='+',symbolPen='g',name='David Neely')
        data=(34,4),(40,5)
        plot.plot(*zip(*data),pen=None,symbol='x',symbolBrush='c',name='Frassetto 2010')
        data=(21,7.6),(40,7.7)
        plot.plot(*zip(*data),pen=None,symbol='s',symbolBrush='b',name='Edelstein 1984')
        gl.nextRows()
        return plot
        
    if gl is None:
        glw=pg.GraphicsLayoutWidget()
        plot=plot_gl(glw.ci)
        glw.addLabel(__name__+'.plot_hitachi_1200lpmm_efficiency',colspan=3,color='999999',size='6pt')
        glw.show()
        return glw,plot
    else:
        return plot_gl(gl)
