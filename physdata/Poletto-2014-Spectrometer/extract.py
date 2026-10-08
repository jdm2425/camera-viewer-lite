import numpy as np
from pylab import plot, ginput, show, axis,imread,imshow,gca,ion
ion()
##
im=imread('Poletto-2014-Spectrometer-Fig6.gif')
imshow(im)
show()
##
print("bottom left")
bottom_left_pix=ginput(1)[0]
print("bottom right")
right_pix=ginput(1)[0]
print('upper left')
top_pix=ginput(1)[0]
##
left=0
bottom=-2
right=800
top=1
##
points_pix=ginput(0)
##
x_pix,y_pix=tuple(zip(*points_pix))
gca().plot(x_pix,y_pix,'o')
##
def pix_to_data(x_pix,y_pix):
    x=(x_pix-bottom_left_pix[0])/(right_pix[0]-bottom_left_pix[0])*(right-left)+left
    y=(y_pix-bottom_left_pix[1])/(top_pix[1]-bottom_left_pix[1])*(top-bottom)+bottom
    return x,y

x,y=zip(*[pix_to_data(x_pix,y_pix) for x_pix,y_pix in points_pix])
eV=np.array(x)
counts_per_photon=10**np.array(y)
print(repr(eV))
print(repr(counts_per_photon))



