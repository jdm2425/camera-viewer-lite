from distutils.core import setup, Extension
import numpy.distutils.misc_util
import os

WinNTFolder=os.path.join("C:\\","Program Files (x86)","IVI Foundation","VISA","WinNT")

visapath  = os.path.join(WinNTFolder,"include")
libx64    = os.path.join(WinNTFolder,"Lib_x64","msc")
libnorm   = os.path.join(WinNTFolder,"lib","msc")
numpydirs = numpy.distutils.misc_util.get_numpy_include_dirs()



setup(
    ext_modules=[Extension("_deformer.c", ["_deformer.c", "deformer.c"],
                library_dirs=[visapath,libnorm,libx64],
                libraries = ["nivisa64","TLDFM_64","TLDFMX_64","visa64"])],
    include_dirs=[numpydirs,visapath,libnorm,libx64],
)

#,"TLDSTP"
