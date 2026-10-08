@echo off
REM If this doesnt work, try the following command:
REM conda install libpython m2w64-toolchain cython
REM [build] > %CONDA_PREFIX%\Lib\distutils\distutils.cfg
REM compiler = mingw32 >> %CONDA_PREFIX%\Lib\distutils\distutils.cfg
REM install Visual Studio for the most recent vcruntime and vcvarsall
REM You may also need to run "pip install pywin32"

python setup.py build_ext --inplace
del _deformer.cp*
copy _deformer\c.cp35-win_amd64.pyd .\_deformer.cp35-win_amd64.pyd