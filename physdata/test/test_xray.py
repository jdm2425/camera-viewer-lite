import numpy as np
from physdata.xray import *
import pyqtgraph_extended as pg

def test_refractive_index():
    # I took these values from http://henke.lbl.gov/optical_constants/getdb2.html
    # on 23/9/2016
    assert np.isclose(refractive_index('Ne',300,0.8999)-1,-1.81337089E-06+3.28078897E-07j)
    assert np.isclose(refractive_index('Ar',200,1.784)-1,-1.82901158E-06+6.52095139E-07j)
    assert np.isclose(refractive_index('Al',400,2.699e3)-1,-0.00317348377+0.000863814494j,rtol=1e-3)
    
def test_andor_resonse(qtbot):
    eV=np.logspace(1,3)
    cpp=interp_andor_ccd_response(eV)
    plt=pg.PlotWindow(labels={'bottom':'eV','left':'counts/photon'})
    plt.plot(eV,cpp)
    
def test_pixis_response(qtbot):
    ##
    eV,cpp=get_pixis_xo_400b_response()
    plt=pg.PlotWindow(labels={'bottom':'eV','left':'counts/photon'})
    plt.plot(eV,cpp)
    ##
def test_poletto_2014_response(qtbot):
    ##
    plt=pg.PlotWindow(title='Poletto 2014 response',labels={'bottom':'eV','left':'counts/photon'})
    pg.addLegend(plt.plotItem)
    for lpmm,color in zip((1200,2400),pg.tableau10):
        eV,cpp=get_poletto_2014_response(lpmm)
        plt.plot(eV,cpp,pen=color,name='%d /mm'%lpmm)
    ##
def test_hitachi_grating_efficiency(qtbot):
    ##
    plt=pg.PlotWindow(title='Hitachi grating efficiency',labels={'bottom':'eV','left':'efficiency'})
    pg.addLegend(plt.plotItem)
    for lpmm,color in zip((1200,2400),pg.tableau10):
        eV,eff=get_hitachi_grating_efficiency(lpmm)
        plt.plot(eV,eff,pen=color,name='%d /mm'%lpmm)
    ##  
    
def test_photonis_mcp_efficiency(qtbot):
    ##
    plt=pg.PlotWindow(labels={'bottom':'eV','left':'efficiency'})
    pg.addLegend(plt.plotItem)
    for coating,color in zip(('uncoated','CsI','MgF2'),pg.tableau10):
        for smooth in False,True:
            eV,eff=get_photonis_mcp_efficiency(coating,smooth)
            plt.plot(eV,eff,pen=color,name=coating if smooth else None)
    ##
    
def test_interp_hitachi_photonis_efficiency(qtbot):
    ##
    plt=pg.PlotWindow(labels={'bottom':'eV','left':'efficiency'})
    eV=np.linspace(12,28)
    eff=interp_hitachi_photonis_efficiency(eV,1200,'uncoated')
    plt.plot(eV,eff)
    ##
if __name__=="__main__":
    # test_refractive_index()
    # test_andor_resonse(None)
    # test_poletto_2014_response(None)
    # test_hitachi_grating_efficiency(None)
    #test_photonis_mcp_efficiency(None)
    #test_interp_hitachi_photonis_efficiency(None)
    test_pixis_response(None)
