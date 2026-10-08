from physdata import xray
import pyqtgraph_extended as pg
##
glw=pg.GraphicsLayoutWidget()
plot=glw.addAlignedPlot(labels={'left':'QE','bottom':'photon energy (eV)'},title='XUV CCD camera quantum efficiencies')
pg.addLegend(plot,offset=(1,1),background_color='00000000',border_color='00000000')
for micron,color in zip((15,40),pg.tableau10):
    plot.plot(*xray.get_andor_ccd_qe(micron),name='Andor %d micron no AR'%micron,pen=color)
plot.plot(*xray.get_pixis_xo_400b_qe(),name='PI PIXIS XO 400b',pen=pg.tableau10[2])
plot.setLogMode(x=True)
glw.show()
pg.export(glw,'XUV_CCD_QEs','svg-pdf-png')
