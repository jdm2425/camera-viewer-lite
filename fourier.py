"""Fourier transforms with full broadcasting support

Functions and classes for approximating the (continuous) Fourier transform
with the discrete Fourier transform. Deals with calculation of the sampling
points, shifting and normalising.

The code supports arbitrary dimension arrays using the Numpy broadcasting
semantics. axis indices are negative i.e. counting from the trailing dimension,
since this is the way Numpy works.
"""
import math
from collections import OrderedDict
import numpy as np
import mathx as mx
import mathx.uniformly_spaced_vector as usv
from math import sqrt, pi
#%%


def swap_axes(a, axis1, axis2):
    """Swaps two axes of an array, expanding the array if necessary."""
    shape_pad_right = max(axis1-a.ndim+1, axis2-a.ndim+1, 0)
    shape_pad_left = max(-axis1-a.ndim, -axis2-a.ndim, 0)
    print('TODO')


def trans_to_arb(x, sign, Ex, k, axis=None):
    """Fourier transform uniformly sampled array to arbitrarily sampled points."""
    x = np.asarray(x)
    k = np.asarray(k)
    if axis is None:
        axis = mx.last_axis(x)
    Dx = np.diff(np.take(x, [0, 1], axis=axis), axis=axis)
    if -k.ndim <= axis < k.ndim and k.shape[axis] > 1:
        # k spans the transform dimension. Insert an extra dimension in the
        # input arrays so x and k can be broadcast
        Ex = np.expand_dims(Ex, axis)
        x = np.expand_dims(x, axis)
        sum_axis = axis-1
        k = np.expand_dims(k, sum_axis)
        keepdims = False
    else:
        sum_axis = axis
        keepdims = True
    #return np.sum(np.exp(1j*sign*x*k)*Ex, axis=sum_axis, keepdims=keepdims)*(Dx/sqrt(2*pi))
    return mx.multiply_and_sum((np.exp(1j*sign*x*k), Ex), sum_axis, keepdims)*(Dx/sqrt(2*pi))


def trans_to_arb_ND(xs, signs, Ex, ks, axes):
    """N-dimensional Fourier transform to arbitrarily sampled points.
    xs is a list of the sampling points along which to transform, signs the corresponding
    signs of the exponent, and ks a list of the components of the k-vectors
    to evaluate. Ex is the original array. xs, Ex and ks must be mutually 
    broadcastable except ks may differ along axes (since these are summed over and
    reduced by the transform).
    """
    squeeze_dim_inds = []
    for n in range(len(axes)):
        axis = axes[n]
        ks_shape = np.broadcast(*ks).shape
        if -len(ks_shape) <= axis < len(ks_shape) and ks_shape[axis] != 1:
            # transformation axis is spanned by ks. Insert additional axis
            # so they are different
            xs = [np.expand_dims(x, axis) for x in xs]
            Ex = np.expand_dims(Ex, axis)
            # Call mathx.expand dims because of strange np behaviour
            ks = [mx.expand_dims(k, axis-1) for k in ks]
            # Shift dimension indices along
            for m in range(len(axes)):
                if axes[m] <= axes[n]:
                    axes[m] = axes[m]-1
            squeeze_dim_inds.append(n)
    # Evaluate transform
    for x, sign, k, axis in zip(xs, signs, ks, axes):
        Dx = np.diff(np.take(x, [0, 1], axis), axis=axis)
        Ex = np.sum(np.exp(1j*sign*x*k)*Ex, axis, keepdims=True)*Dx/sqrt(2*pi)
    # Squeeze out the inserted working dimensions
    Ex = np.squeeze(Ex, tuple(axes[ind] for ind in squeeze_dim_inds))
    # Squeeze out singleton leading dimensions
    Ex = mx.squeeze_leading(Ex)
    return Ex


def conj_axis(t, offset=0, offset_type='middle', axis=None):
    if axis is None:
        axis = mx.last_axis(t)
    Dt = np.diff(np.take(t, [0, 1], axis), axis=axis)
    N = t.shape[axis]
    Dw = 2*pi/(N*Dt)
    if offset_type == 'middle':
        n_o = N/2
    elif offset_type == 'middle_index':
        n_o = int(N/2)
    elif offset_type == 'start':
        n_o = 0
    elif offset_type == 'end':
        n_o = N-1
    else:
        raise ValueError('Unknown offset_type ', offset_type)
    n = mx.reshape_vec(np.arange(N), axis)-n_o
    return offset+n*Dw


def trans(x, sign, Ex, k, axis=None):
    """
    Args:
        x: sampling points, must be uniform
        sign: sign of exponent in transform
        Ex: array to transform
        k: conjugate axis to x
        axis: axis to transform along
    """
    ftd = FTD(sign, axis, x=x, k=k)
    return ftd.trans(Ex)


def trans_oversample(x, sign, Ex, k, factor=1, axis=None):
    if axis is None:
        axis = mx.last_axis(x)
    num_pad = int(len(x)*factor/2)
    xo, Exo = usv.pad_sampled(x, Ex, num_pad, num_pad, axis)
    ko = conj_axis(xo, k[0], 'start', axis)
    Eko = trans(xo, sign, Exo, ko, axis)
    return ko, Eko, xo


def oversample(x, Ex, factor=1, axis=None):
    if axis is None:
        axis = mx.last_axis(x)
    k = conj_axis(x)
    Ek = trans(x, -1, Ex, k, axis)
    return trans_oversample(k, 1, Ek, x, factor, axis)


def trans_ND(xs, signs, Ex, ks, axes=None):
    if axes is None:
        axes = [mx.vector_dim(x) for x in xs]
    for x, sign, k, axis in zip(xs, signs, ks, axes):
        Ex = trans(x, sign, Ex, k, axis)
    return Ex


class FTD:
    """Represents Fourier transform (FT), approximated by the discrete Fourier 
    transform with a particular discretization. Handles bandlimited signals located
    arbitrarily in space/conjugate space.

    Internally, all axis parameters (x_0, Dx, etc) are numpy arrays (to make objects strictly identical). They do not
    need to be passed to __init__ as such.
    """

    def __init__(self, sign=-1, axis=None, **kwargs):
        """N is number of samples, x_0 is first x sample, Dx is x spacing, i.e. x_n=x_0+n*Dx,
        X is N*Dx. x_m is the middle = x_0+(N-1)*Dx/2. All of these are defined
         similarly for k. Can specify any combination of them with sufficient information
         to define the sampling axes. If unspecified, x_0 and k_0 default to 0."""
        for key in kwargs.keys():
            if key not in ('N', 'x', 'x_0', 'Dx', 'x_m', 'x_middle_ind', 'X', 'k', 'k_0', 'Dk', 'k_m', 'k_middle_ind', 'K'):
                raise ValueError('Unknown argument %s' % key)
        self.sign = sign
        if axis is not None:
            if axis >= 0:
                raise TypeError(
                    'axis must be negative (because numpy broadcasts starting from trailing dimensions)')
            self.axis = axis
        elif 'x' in kwargs:
            self.axis = mx.last_axis(kwargs['x'])
        elif 'k' in kwargs:
            self.axis = mx.last_axis(kwargs['k'])
        else:
            self.axis = -1
        # Determine N
        if 'N' in kwargs:
            self.N = kwargs['N']
        elif 'x' in kwargs:
            self.N = kwargs['x'].shape[self.axis]
        elif 'k' in kwargs:
            self.N = kwargs['k'].shape[self.axis]
        elif 'Dx' in kwargs and 'X' in kwargs:
            self.N = math.ceil(kwargs['X']/kwargs['Dx'])
        elif 'Dk' in kwargs and 'K' in kwargs:
            self.N = math.ceil(kwargs['K']/kwargs['Dk'])
        elif 'Dx' in kwargs and 'Dk' in kwargs:
            self.N = math.ceil(2*pi/(kwargs['Dx']*kwargs['Dk']))
        elif 'X' in kwargs and 'K' in kwargs:
            self.N = math.ceil(kwargs['X']*kwargs['K']/(2*pi))
        else:
            raise ValueError('N undetermined by arguments')
        self.N = np.unique(self.N)
        if len(self.N) > 1:
            raise ValueError('Only one N allowed')
        self.N = self.N[0]
        # Determine Dx
        Dx = None
        if 'x' in kwargs:
            Dx = np.diff(
                np.take(kwargs['x'], [0, 1], self.axis), axis=self.axis)
        elif 'Dx' in kwargs:
            Dx = kwargs['Dx']
        elif 'X' in kwargs:
            Dx = kwargs['X']/self.N
        if Dx is not None:
            self.Dx = np.array(Dx)
            self.Dk = 2*pi/(self.N*self.Dx)
        else:
            if 'k' in kwargs:
                Dk = np.diff(
                    np.take(kwargs['k'], [0, 1], axis=self.axis),
                    axis=self.axis)
            elif 'Dk' in kwargs:
                Dk = kwargs['Dk']
            elif 'K' in kwargs:
                Dk = kwargs['K']/self.N
            else:
                raise ValueError('Dx and Dk undetermined by arguments')
            self.Dk = np.asarray(Dk)
            self.Dx = 2*pi/(self.N*self.Dk)
        # Determine x_0
        if 'x' in kwargs:
            x_0 = np.take(kwargs['x'], [0], axis=self.axis)
        elif 'x_0' in kwargs:
            x_0 = kwargs['x_0']
        elif 'x_m' in kwargs:
            x_0 = kwargs['x_m']-(self.N-1)*self.Dx/2
        elif 'x_middle_ind' in kwargs:
            x_0 = kwargs['x_middle_ind']-round(self.N/2)*self.Dx
        else:
            x_0 = 0
        self.x_0 = np.asarray(x_0)
        # Determine k_0
        if 'k' in kwargs:
            k_0 = np.take(kwargs['k'], [0], axis=self.axis)
        elif 'k_0' in kwargs:
            k_0 = kwargs['k_0']
        elif 'k_m' in kwargs:
            k_0 = kwargs['k_m']-(self.N-1)*self.Dk/2
        elif 'k_middle_ind' in kwargs:
            k_0 = kwargs['k_middle_ind']-round(self.N/2)*self.Dk
        else:
            k_0 = 0
        self.k_0 = np.asarray(k_0)
        # Setup arrays
        n = mx.reshape_vec(np.arange(self.N), self.axis)
        self.x = self.x_0+self.Dx*n
        self.k = self.k_0+self.Dk*n
        self.X = self.Dx*self.N
        self.K = self.Dk*self.N
        self.x_fac = np.exp(1j*self.sign*self.k_0*self.Dx*n)
        self.k_fac = np.exp(1j*self.sign*self.x_0*self.Dk*n)
        self.fac = np.exp(1j*self.sign*self.x_0*self.k_0)*sqrt(self.N/(2*pi))

    def trans(self, E):
        if self.sign == -1:
            fun = np.fft.fft
            fac = 1/sqrt(self.N)
        else:
            fun = np.fft.ifft
            fac = sqrt(self.N)
        return fac*self.fac*self.k_fac*fun(E*self.x_fac, axis=self.axis)*self.Dx

    def inv_trans(self, E):
        if self.sign == -1:
            fun = np.fft.ifft
            fac = sqrt(self.N)
        else:
            fun = np.fft.fft
            fac = 1/sqrt(self.N)
        return fac*np.conj(self.fac*self.x_fac)*fun(E*np.conj(self.k_fac), axis=self.axis)*self.Dk

    def inv_trans_padded(self, Ek, b, a):
        ko, Eko = usv.pad_sampled(self.k, Ek, b, a, self.axis)
        xo = conj_axis(ko, self.x[0], 'start')
        return ko, trans(ko, -self.sign, Eko, xo)

    def inv_trans_arb(self, E, xp):
        """Inverse transform to arbitrary sampling points."""
        return trans_to_arb(self.k, -self.sign, E, xp, self.axis)

    def trans_arb(self, E, kp):
        """Transform to arbitrary sampling points."""
        return trans_to_arb(self.x, self.sign, E, kp, self.axis)

    def norm(self, E, conj=False):
        sc = self.Dk if conj else self.Dx
        return np.sum(mx.abs_sqd(E), axis=self.axis, keepdims=True)*sc

    def kwargs(self):
        return OrderedDict([(k, getattr(self, k)) for k in ('x_0', 'Dx', 'N', 'k_0', 'axis', 'sign')])

    def scaled(self, x_fac, cls=None):
        """Self with x-axis multiplied by x_fac and k-axis divided by x_fac."""
        if cls is None:
            cls = type(self)
        return cls(x_0=self.x_0*x_fac, Dx=self.Dx*x_fac, k_0=self.k_0/x_fac, N=self.N, sign=self.sign, axis=self.axis)

    def x_sliced(self, slc):
        return type(self)(x=self.x[slc], k_0=self.k_0, sign=self.sign, axis=self.axis)

    def k_sliced(self, slc):
        return type(self)(k=self.k[slc], x_0=self.x_0, sign=self.sign, axis=self.axis)

    def __eq__(self, other):
        return (type(self) is type(other)
                and self.N == other.N
                and np.array_equal(self.Dx, other.Dx)
                and np.array_equal(self.x_0, other.x_0)
                and np.array_equal(self.k_0, other.k_0)
                and self.sign == other.sign)

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return type(self).__name__+'(N=%d,x_0=%g,Dx=%g,k_0=%g)' % (self.N, self.x_0, self.Dx, self.k_0)

    def __getstate__(self):
        return self.kwargs()

    def __setstate__(self, state):
        self.__init__(**state)

    def __repr__(self):
        return type(self).__name__+'(**'+repr(self.__getstate__())+')'


from physdata import SI
from params import ParameterTree


class TimeFreqAtomicUnitsFTD(FTD):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t = self.x
        self.omega = self.k
        self.eV = self.omega*SI['E_h']/SI['e']


class TimeFreqSIOptFTD(FTD):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t = self.x
        self.omega = self.k
        # lambda is a keyword in Python - one can use it for attributes but
        # for consistency's sake we use lamb throughout
        self.lamb = 2*np.pi*SI['c']/self.omega
        self.eV = self.omega*SI['hbar']/SI['e']


def spectrogram(t, sign, Et, Gt, omega, bound_cond='pad'):
    assert bound_cond in ('pad', 'odd-cyclic', 'cyclic')
    if not type(Gt) == np.array:
        nG = Gt
        ga = np.arange(nG)-(nG-1.0)/2
        Gt = np.exp(-(5*ga/nG)**2)
#            plt.figure()
#            plt.plot(ga,Gt)
    else:
        nG = Gt.size
    Dt = t[1]-t[0]
    t_G = np.arange(nG)*Dt
    if bound_cond == 'pad':
        t, Et = usv.pad_sampled(t, Et, nG, nG)
    omega_s = conj_axis(t_G, omega[0], 'start')
    ft = FTD(sign, x=t_G, k=omega_s)
    if bound_cond in ('cyclic', 'odd-cyclic'):
        tsis = np.arange(t.size)-int(nG/2)
    else:
        tsis = np.arange(t.size-Gt.size)
    t_s = t[0]+(tsis+nG/2)*Dt
    S = np.zeros((omega_s.size, t_s.size))
    for tsii in range(len(tsis)):
        tsi = tsis[tsii]
        inds = np.arange(tsi, tsi+nG)
        if bound_cond == 'odd-cyclic':
            sign = (-1)**np.floor(inds/t.size)
        else:
            sign = 1
        if bound_cond in ('cyclic', 'odd-cyclic'):
            inds = inds % t.size
        S[:, tsii] = mx.abs_sqd(ft.trans(Et[inds]*Gt*sign))
    return (t_s, omega_s, S)
