"""General mathematical functions"""
import numpy as np
import math,logging
from itertools import zip_longest
import scipy
import scipy.special
from . import *
logger=logging.getLogger(__name__)

def asscalar(x):
    """Like Numpy's asscalar but handles inputs that are already scalar."""
    return np.asarray(x).item()

def reshape_vec(vec,axis):
    """Reshape array to lie along given axis.
    
    If axis>=0, reshapes vec to (1,...,1,n) where the number of ones is axis and
    n is the number of elements. If axis<0, reshapes vec to (n,1,..,1) where 
    the number of ones is -(axis+1).""" 
    vec=np.array(vec)
    if axis>=0:
        return vec.reshape((1,)*axis+(-1,))
    else:
        return vec.reshape((-1,)+(1,)*-(axis+1))
        
def vector_dim_shape(shape):
    """Returns the dimension (negative) spanned by a vector of given shape.
    ValueError if more
    than one dimension is greater than 1. If no dimensions greater than 1, returns
    the leftmost."""
    ndim=len(shape)
    dims=np.greater(shape,1).nonzero()[0]-ndim
    if dims.size>1:
        raise ValueError('Multiple dimensions '+str(dims)+' great than 1.')
    if dims.size==0:
        return -ndim
    else:
        return dims[0]
        
def vector_dim(a):
    """Returns the dimension (negative) spanned by a vector. ValueError if more
    than one dimension is greater than 1. If no dimensions greater than 1, returns
    the leftmost."""
    return vector_dim_shape(np.asarray(a).shape)
    
def nonzero_vec(vec):
    """Nonzero elements of vec as a vector along the dimension of vec.
    
    Useful for advanced indexing.
    """
    vec=np.asarray(vec)
    dim=vector_dim(vec)
    return reshape_vec(vec.nonzero()[dim],dim)
    
def expand_dims(k,axis):
    """Like np.expand_dims, but corrects weird numpy behaviour.
    
    I found that:
    np.expand_dims(np.zeros((3,2)),-4).shape
    gives
    (3,1,2)
    which doesn't make much sense.
    
    This function calls expand dims if axis is spanned by k, otherwise returns
    k doing nothing.
    """
    if -k.ndim<=axis<=k.ndim:
        return np.expand_dims(k,axis)
    else:
        return k

def squeeze_leading(x):
    """Squeeze leading singleton dimensions."""
    x=np.asarray(x)
    n=next((n for n in range(x.ndim) if x.shape[n]>1),x.ndim)
    x=np.squeeze(x,tuple(range(n)))
    if x.ndim==0:
        x=x.item()
    return x
        
def insert_dim(a,axis):
    # Not sure if this function is really necessary
    if axis>=0 or axis<0 and -axis<=a.ndim:
        return np.expand_dims(a,axis)
    else:
        return a
        
def argmax(a,axis=-1):
    """Indices of maximum value along given axis.
    Differs from numpy.argmax in that axis isn't removed from the shape."""
    return np.expand_dims(np.argmax(a,axis),axis)
        
def ind_closest(array,value,axis=None):
    """Element in array closest to the scalar value."""
    idx=np.abs(array-value).argmin(axis)
    if axis is not None:
        idx=insert_dim(idx,axis)
    return idx
    
def broadcasted_shape(*shapes):
    shape=[]
    for lengths in zip_longest(*[shape[::-1] for shape in shapes],fillvalue=1):
        max_length=max(lengths)
        assert all(length==1 or length==max_length for length in lengths)
        shape.append(max_length)
    return tuple(shape[::-1])
    
def are_shapes_broadcastable(*shapes):
    """Test if shapes are Numpy broadcastable."""
    for lengths in zip_longest(*[shape[::-1] for shape in shapes],fillvalue=1):
        max_length=max(lengths)
        if not all(length==1 or length==max_length for length in lengths):
            return False
    return True

def are_broadcastable(*arrays):
    return are_shapes_broadcastable(*[np.shape(array) for array in arrays])
    
def shapes_equal_trailing(*shapes):
    """Test if shapes are equal, starting from trailing end, except for leading ones."""
    for lengths in zip_longest(*[shape[::-1] for shape in shapes],fillvalue=1):
        if not all(length==lengths[0] for length in lengths):
            return False
    return True
   
def set_shape_element(shape,index,value):
    """Set element of shape tuple, adding ones if necessary.
    Examples:
        set_shape_element((2,3),2,4)=(2,3,1,4)
        set_shape_element((2,3),-4,4)=(4,1,2,3)
    """
    if index>=0:
        return shape[:index]+(1,)*(index-len(shape))+(value,)+shape[index+1:]
    else:
        if index==-1:
            trailing=()
        else:
            trailing=shape[index+1:]
        return shape[:index]+(value,)+(1,)*(-index-len(shape)-1)+trailing
        
def broadcasted_size_along(shape,axis):
    assert axis<len(shape),'Only makes sense axis less than number of dimensions (including negative)'
    if axis>=0:
        return shape[axis]
    elif -axis<=len(shape):
        return shape[axis]
    else:
        return 1

def all_axes_except(ndim,axis):
    return tuple(range(-ndim,axis))+tuple(range(axis+1,0))
    
def off_diag(a):
    """Return off-diagonal elements of array. TODO: semantics for >2 dimensions"""
    n=np.arange(min(a.shape))
    return a[n[:,None]!=n]
    
def flip(a,axis):
    """Flip array along arbitrary axis."""
    a=np.asarray(a)
    if axis>=0:
        return a[[slice(None)]*axis+[slice(None,None,-1)]+[Ellipsis]]
    elif -axis<=a.ndim:
        return a[[Ellipsis]+[slice(None,None,-1)]+[slice(None)]*(-axis-1)]
    else:
        return a
    
def gal(x,a,b):
    return (x>a)&(x<b)

def geale(x,a,b):
    """Greater than or equal to and less than or equal to."""
    return (x>=a)&(x<=b)

def abs_sqd(x):
    return np.real(x*np.conj(x))
    
def norm_max(x,axis=None):
    return x/np.amax(x,axis,keepdims=True)

def norm_sum(x,axis=None):
    return x/np.sum(x,axis,keepdims=True)

def last_axis(a):
    """Negative index of last nonsingleton axis of an array
        e.g. if a has shape (1,3,4,1) then last_axis(a) returns -2"""
    return np.nonzero(np.array(a.shape)!=1)[0][-1]-a.ndim
    
def diff(x,n=1,axis=None):
    """Central finite difference with non-centred for at edges.
    
    Returns:
        array: same size as x
    """
    if axis is None:
        axis=last_axis(x)
    x=np.swapaxes(x,axis,0)
    for _ in range(n):
        x=np.concatenate((x[[1]]-x[[0]],(x[2:]-x[:-2])/2,x[[-1]]-x[[-2]]),0)
    return np.swapaxes(x,axis,0)
        
def diff_arb(x,y,axis=None):
    """Finite difference for non-uniformly sampled array. TODO boundary values"""
    if axis==None:
        axis=last_axis(x)
    x=np.swapaxes(x,axis,-1)
    y=np.swapaxes(y,axis,-1)
    x0=x[...,:-2]
    x1=x[...,1:-1]
    x2=x[...,2:]
    y0=y[...,:-2]
    y1=y[...,1:-1]
    y2=y[...,2:]
    f = (x2 - x1)/(x2 - x0)
    return np.swapaxes((1-f)*(y2 - y1)/(x2 - x1) + f*(y1 - y0)/(x1 - x0),axis,-1)
    
def interp_at(x,y,x_0,der=0,axis=None):
    x=np.array(x)
    y=np.array(y)
    if axis==None:
        axis=last_axis(x)
    i_0=np.abs(x-x_0).argmin()
    i_s=max(i_0-1,0)
    i_m=min(i_0+2,x.shape[axis])
    return scipy.interpolate.krogh_interpolate(x[...,i_s:i_m],y[...,i_s:i_m],x_0,der)

class interp1d_rect:
    def __init__(self,x,y,kind='linear',axis=-1,copy=True,bounds_error=None,fill_value=float('nan'),assume_sorted=False):
        self.real=scipy.interpolate.interp1d(x,y.real,kind,axis,copy,bounds_error,fill_value,assume_sorted)
        self.imag=scipy.interpolate.interp1d(x,y.imag,kind,axis,copy,bounds_error,fill_value,assume_sorted)
    def __call__(self,xi):
        return self.real(xi)+1j*self.imag(xi)
        
class interp1d_polar:
    def __init__(self,x,y,kind='linear',axis=-1,copy=True,bounds_error=None,fill_value=float('nan'),assume_sorted=False):
        self.abs=scipy.interpolate.interp1d(x,abs(y),kind,axis,copy,bounds_error,fill_value,assume_sorted)
        self.phi=scipy.interpolate.interp1d(x,np.unwrap(np.angle(y),axis=axis),kind,axis,copy,bounds_error,fill_value,assume_sorted)
    def __call__(self,xi):
        return self.abs(xi)*np.exp(1j*self.phi(xi))
        


def take_broadcast_inds(shape,inds,axis):
    """Object for indexing along given axis with broadcasting shape.
    
    This  function returns a selection object for taking indices inds of
    an array of shape along axis. The difference from numpy.take is in the
    treatment of multidimensional inds. Instead of replacing shape[axis] with
    inds.shape in the shape of the result (as in the numpy docs example below), 
    this function broadcasts inds with shape. 
    
    From the numpy docs:
        Let x.shape be (10,20,30,40,50) and suppose ind_1 and ind_2 can be
        broadcast to the shape (2,3,4). Then x[:,ind_1,ind_2] has shape
        (10,2,3,4,40,50) because the (20,30)-shaped subspace from X has been
        replaced with the (2,3,4) subspace from the indices.
    """
    if axis>=0:
        axis=axis-len(shape)
    bc_inds=[(reshape_vec(range(shape[n]),n) if n!=axis else inds) for n in range(-len(shape),0)]
    return bc_inds
    
def take_broadcast(array,inds,axis=None ):
    if axis is None:
        axis=vector_dim(array)
    return array[take_broadcast_inds(array.shape,inds,axis)]

# def take_multi(array,inds,axes):
#     """Take multiple times
#     
#     Args:
#         inds: sequence of indices or index arrays
#         axes: sequence of axes
#     """
#     return array[slice_dims(inds,axes)]
        

# def index_multi(array,indss,axes):
#     array=np.asarray(array)
#     tmp=[]
#     for inds,axis in zip(indss,axes):
#         inds=np.asarray(inds)
#         if -array.ndim<=axis<array.ndim:
#             if array.shape[axis]==1:
#                 # take can remove dimension or add dimensions - need to mimic this
#                 tmp.append((np.zeros(np.ones(inds.ndim,int),int),axis))
#             else:
#                 tmp.append((inds,axis))
#     if len(tmp)==0:
#         return array
#     indss,axes=zip(*tmp)
#     return array[slice_dims(indss,axes)]

class Interp1D:
    def __init__(self,x,xi,axis=None,extrap=False):
        x=np.asarray(x)
        if axis is None:
            axis=vector_dim(x)
        neps=get_frac_inds(x,xi,axis)
        n=np.clip(np.floor(neps).astype(int),0,x.shape[axis]-2)
        eps=neps-n
        if not extrap:
            eps=np.clip(eps,0,1)
        self.n=n
        self.eps=eps
        self.axis=axis

    def __call__(self,y):
        return interp1d_n_eps(y,self.n,self.eps,self.axis)

def interp1d(x,y,xi,axis=None,extrap=False,assume_x_uniform=False):
    """

    Args:
        x:
        y:
        xi:
        axis:
        extrap:
        assume_x_uniform (bool): if x is uniformly spaced.

    Returns:

    """
    if assume_x_uniform:
        yi=interp1d_assume_uniform(x,y,xi,axis,extrap)
    else:
        yi=Interp1D(x,xi,axis,extrap)(y)
    return yi
    
def interp1d_to_uniform(x,y,axis=None):
    """Resample array to uniformly sampled axis.
    
    Has some limitations due to use of scipy interp1d.
    
    Args:
        x (vector): independent variable
        y (array): dependent variable, must broadcast with x
        axis (int): axis along which to resample
    
    Returns:
        xu: uniformly spaced independent variable
        yu: dependent resampled at xu
    """
    x=np.asarray(x)
    y=np.asarray(y)
    if axis is None:
        axis=vector_dim(x)
    num=x.shape[axis]
    mn=x.min(axis,keepdims=True)
    mx=x.max(axis,keepdims=True)
    # Limitation of scipy interp1d
    x=x.squeeze()
    mn=mn.squeeze()
    mx=mx.squeeze()
    assert x.ndim==1
    xu=np.arange(num)/(num-1)*(mx-mn)+mn
    yu=scipy.interpolate.interp1d(x.squeeze(),y,axis=axis,bounds_error=False)(xu)
    return reshape_vec(xu,axis),yu

def interp1d_n_eps(y,n,eps,axis):
    """Interpolate array at index specified by integer and offset.

    Args:
        y (array): to interpolate
        n (array of int): index, must be 0<=n<=y.shape[axis]-2.
        eps (array of float): offset. If outside [0,1], extrapolation is performed implicitly.

    Returns:
        array: y sampled at n+eps
    """
    return take_broadcast(y,n,axis)*(1-eps)+take_broadcast(y,n+1,axis)*eps

class Interp1DUniform:
    def __init__(self,x0,Dx,N,axis,xi,extrap=True):
        """
        Args:
            axis (int): interpolation axis. If None, chooses based on y, which in that
                case must be a vector.
            extrap (bool): if True, use linear extrapolation based on the extreme values.
                If false, nearest neighbour is used for extrapolation instead.
        """
        xi=np.array(xi,ndmin=1,copy=False)
        nf=(xi-x0)/Dx
        n=np.floor(nf).astype(int)
        n[n>=N-1]=N-2
        n[n<0]=0
        eps=nf-n
        if not extrap:
            eps=np.clip(eps,0,1)
        self.n=n
        self.eps=eps
        self.axis=axis

    def __call__(self,y):
        return interp1d_n_eps(y,self.n,self.eps,self.axis)
        
def interp1d_assume_uniform(x,y,xi,axis=None,extrap=True):
    x=np.asarray(x)
    if axis is None:
        axis=vector_dim(x)
    x0=x.take([0],axis)
    Dx=x.take([1],axis)-x0
    yi=interp1d_lin_reg(x0,Dx,y,xi,axis,extrap)
    return yi

def interp1d_lin_reg(x0,Dx,y,xi,axis=None,extrap=True):
    """
    Args:
        axis (int): interpolation axis. If None, chooses based on y, which in that
            case must be a vector.
        extrap (bool): if True, use linear extrapolation based on the extreme values.
            If false, nearest neighbour is used for extrapolation instead.
    """
    y=np.asarray(y)
    if axis is None:
        axis=vector_dim(y)
    interp=Interp1DUniform(x0,Dx,y.shape[axis],axis,xi,extrap)
    return interp(y)

def interp1d_frac_ind(y,xi,axis=None):
    """Lookup/resample array at fractional indices using linear interpolation.
    
    Args:
        y: array to resample
        xi: fractional indices
        axis (int): axis indexed by xi
    
    Returns:
        y indexed at xi
    """
    return interp1d_lin_reg(0,1,y,xi,axis)
    
def find_first_nonzero(x,axis=None):
    """Find indices of first nonzero element along given axis.
    
    Where there is no nonzero element, the size of x along axis is returned.
    """
    x=np.asarray(x)
    if axis is None:
        axis=vector_dim(x)
    nz=x!=0
    res=nz.argmax(axis)
    res=np.expand_dims(res,axis)
    no_nz=~nz.any(axis,keepdims=True)
    res[no_nz]=broadcasted_size_along(x.shape,axis)
    #res=squeeze_leading(res)
    return res
    
def find_last_nonzero(x,axis=None):
    """Find indices of last nonzero element along given axis.
    
    Where there is no nonzero element, -1 is returned."""
    x=np.asarray(x)
    if axis is None:
        axis=vector_dim(x)
    xf=flip(x,axis)
    resf=find_first_nonzero(xf,axis)
    sx=broadcasted_size_along(x.shape,axis)
    res=sx-1-resf
    return res
    
def get_frac_inds(x,xp,axis=None,suppress_degeneracy_error=False):
    """Get fractional indices using linear interpolation.
    
    For any xp outside the range of x, linear extrapolation based on the closest
    two values of x is used. If these two values are equal, then an inf will result.
    
    Result is array with squeezed leading dimensions.
    
    Args:
        x (array): must be nondecreasing along axis.
    """
    x=np.asarray(x)
    if axis is None:
        axis=vector_dim(x)
    # Because we iterate over xp along axis, it needs to have this dimension
    xp_ndim_orig=np.ndim(xp)
    xp=np.array(xp,ndmin=-axis)
    lx=broadcasted_size_along(x.shape,axis)
    def get_xixpt(xpi):
        xpt=take_broadcast(xp,[xpi],axis)
        # Find index of xb, the last value of x which is less than or equal to xpt
        xib=find_last_nonzero(x<=xpt,axis)
        # Find index of xa, the first value of x which is greater than xpt
        xia=find_first_nonzero(x>xpt,axis)
        # If all elements of x are greater than xpt, use zeroth and first i.e.
        # linearly extrapolate
        inds=xib==-1
        xib[inds]=0
        xia[inds]=1
        # Likewise if all elements of x are smaller than or equal to xpt, use
        # second last and last elements
        inds=xia==lx
        xib[inds]=lx-2
        xia[inds]=lx-1
        # Get before and after values of x
        xb=take_broadcast(x,xib,axis)
        xa=take_broadcast(x,xia,axis)
        Dx=xa-xb
        if suppress_degeneracy_error:
            delta=divide0(xpt-xb,Dx)
        else:
            assert Dx.min()>0
            delta=(xpt-xb)/Dx
        xixpt=xib+delta
        return xixpt
    xixp=concatenate([get_xixpt(xpi) for xpi in range(broadcasted_size_along(xp.shape,axis))],axis)
    if xixp.ndim==-axis and xixp.shape[axis]==1 and xixp.ndim>xp_ndim_orig:
        # The axis over which we interpolated is the leading one, and has length 1 i.e. wasn't spanned by xp. Therefore
        # its presence is an 'artefact' of the interpolation and it should be removed.
        xixp=xixp[0]
    return xixp
        
def subtract_tangent(x,y,x_0,axis=None):
    if axis==None:
        axis=last_axis(x)
    y_0=interp_at(x,y,x_0,[0,1])
    return y-y_0[0]-(x-x_0)*y_0[1]
    
def dot(x,y=None):
    if y is None:
        y=x
    #if axis is None:
    return sum(xe*ye for xe,ye in zip(x,y))
    
    # s=None
    # for xe,ye in zip(x,y):
    #     if s is None:
    #         s=xe*ye
    #     else:
    #         s=s+xe*ye
    # return s

def dot_along(x,y,axis,keepdim=False):
    if keepdim:
        return sum(x.take([n],axis)*y.take([n],axis) for n in range(x.shape[axis]))
    else:
        return sum(x.take(n,axis)*y.take(n,axis) for n in range(x.shape[axis]))
        
def mat_mult_along(x,y,axis_x,axis_y=None):
    """Multiply matrices spanning arbitrary axes.

    Returns (sum over n)(x_n*y_n) where n runs of axis_x in x and axis_y in y.

    Args:
        x (array): left matrix
        y (array): right matrix
        axis_x (int): axis of x along which to sum
        axis_y (int): axis of y along which to sum. Defaults to axis_x+1

    Returns:
        matrix product
    """
    if axis_y is None:
        axis_y=axis_x+1
    assert x.shape[axis_y]==y.shape[axis_x]
    return sum(x.take([n],axis_y)*y.take([n],axis_x) for n in range(x.shape[axis_y]))
        
def mult_mat_mat(*args):
    """Multiply two matrices for any indexable types."""
    if len(args)==2:
        a,b=args
        return [[sum(ae*be for ae,be in zip(a_row,b_col)) for b_col in zip(*b)] for a_row in a]
    else:
        return mult_mat_mat(args[0],mult_mat_mat(*args[1:]))
        
def mult_mat_vec(a,b):
    """Multiply matrix times vector for any indexable types."""
    return [sum(ae*be for ae,be in zip(a_row,b)) for a_row in a]

def mult_vec_mat(a,b):
    """Multiply vector times matrix for any indexable types."""
    return [sum(ae*be for (ae,be) in zip(a,b_col)) for b_col in zip(*b)]
    
def mult_mat_sc(a,s):
    return [[e*s for e in row] for row in a]
        
def cosine_apod(t,t_0,Dt):
    """If Dt>0, one for t<t_0, cosine from t_0 to t_0+Dt, zero for t>t_0+Dt.
    If Dt<0, one for t>t_0, cosine from t_0 to t_0+Dt, zero for t<t0+Dt."""
    return np.cos(np.maximum(np.minimum((t-t_0)/Dt,1),0)*math.pi/2)**2
    
def cosine_window(t,t1,t2,Dt1,Dt2=None):
    """0 in t<(t1-Dt) and t>(t2+Dt), 1 in t1<t<t2, cosine transitions."""
    t=np.asarray(t)
    if Dt2 is None:
        Dt2=Dt1
    #return np.cos(np.minimum(np.maximum(np.maximum(t-t2,t1-t)/Dt,0),1)*math.pi/2)**2
    return np.cos(np.minimum(np.maximum(np.maximum((t1-t)/Dt1,(t-t2)/Dt2),0),1)*math.pi/2)**2
    
def wrap_to_pm(x,to):
    """Wrap x to [-to,to)."""
    return (x+to)%(2*to)-to

def wrap_to_pmh(x,to2):
    """Wrap x to [-to/2,to/2)."""
    to=to2/2
    return (x+to)%to2-to

def zero_mod_2pi(x):
    """Test if x wrapped to (-pi,pi) is close to zero"""
    return np.allclose(wrap_to_pm(x,math.pi),0)
    
def unwrap(p,ind_fixed=0,axis=-1):
    """Unwrap phase, preserving value at given index.
    Args:
        p (array): phase to unwrap
        ind_fixed (int): index along the unwrap axis to preserve the value of
        axis (int): axis along which to unwrap.
    Returns:
        array: unwrapped phase
    """
    pu=np.unwrap(p,axis=axis)
    pu+=p.take([ind_fixed],axis)-pu.take([ind_fixed],axis)
    return pu

def _sph_harm_norm(order, degree):
    """Normalization factor for spherical harmonics"""
    # we could use scipy.special.poch(degree + order + 1, -2 * order)
    # here, but it's slower for our fairly small degree
    norm = np.sqrt((2 * degree + 1.) / (4 * np.pi))
    if order != 0:
        norm *= np.sqrt(math.factorial(degree - order) /
                        float(math.factorial(degree + order)))
    return norm

def _sph_harm(order, degree, az, pol, norm=True):
    """Evaluate point in specified multipolar moment. [1]_ Equation 4.
    When using, pay close attention to inputs. Spherical harmonic notation for
    order/degree, and theta/phi are both reversed in original SSS work compared
    to many other sources. See mathworld.wolfram.com/SphericalHarmonic.html for
    more discussion.
    Note that scipy has ``scipy.special.sph_harm``, but that function is
    too slow on old versions (< 0.15) for heavy use.
    Parameters
    ----------
    order : int
        Order of spherical harmonic. (Usually) corresponds to 'm'.
    degree : int
        Degree of spherical harmonic. (Usually) corresponds to 'l'.
    az : float
        Azimuthal (longitudinal) spherical coordinate [0, 2*pi]. 0 is aligned
        with x-axis.
    pol : float
        Polar (or colatitudinal) spherical coordinate [0, pi]. 0 is aligned
        with z-axis.
    norm : bool
        If True, include normalization factor.
    Returns
    -------
    base : complex float
        The spherical harmonic value.
    """
    from scipy.special import lpmv

    # Error checks
    if np.abs(order) > degree:
        raise ValueError('Absolute value of order must be <= degree')
    # Ensure that polar and azimuth angles are arrays
    az = np.asarray(az)
    pol = np.asarray(pol)
    if (np.abs(az) > 2 * np.pi).any():
        raise ValueError('Azimuth coords must lie in [-2*pi, 2*pi]')
    if(pol < 0).any() or (pol > np.pi).any():
        raise ValueError('Polar coords must lie in [0, pi]')
    # This is the "seismology" convention on Wikipedia, w/o Condon-Shortley
    if norm:
        norm = _sph_harm_norm(order, degree)
    else:
        norm = 1.
    return norm * lpmv(order, degree, np.cos(pol)) * np.exp(1j * order * az)
    
def sph_harm(l,m,theta,phi):
    """Spherical harmonic using Wikipedia definition, Y^m_l(theta,phi)"""
    return _sph_harm(m,l,phi,theta)
    
def real_sph_harm(l,m,theta,phi):
    """Real-valued spherical harmonics, Wikipedia definition Y_{lm}(theta,phi)."""
    if m<0:
        return 1j/2**0.5*(sph_harm(l,m,theta,phi)-(-1)**m*sph_harm(l,-m,theta,phi))
    elif m==0:
        return sph_harm(l,0,theta,phi)
    else:
        return 1/2**0.5*(sph_harm(l,-m,theta,phi)+(-1)**m*sph_harm(l,m,theta,phi))
        
def line_two_points(x1,y1,x2,y2,x):
    return divide0(y1*(x2-x)+y2*(x-x1),x2-x1,float('nan'))

def peak_crossings_1D(x,y,frac=0.5,ym=None):
    """
    Args:
        x: increasing array
        y: function sampled at x
        ym: if supplied, use as maximum instead
    """
    x=np.asarray(x)
    y=np.asarray(y)
    im=y.argmax()
    if ym is None:
        ym=y[im]
    yc=ym*frac
    # after
    ais=im+(y[im:]<yc).nonzero()[0]
    if len(ais)==0:
        ai=len(x)-1#x[-1]
    else:
        ai=ais[0]
        #a=x[ai]-x[ai-1]
    a=line_two_points(y[ai-1],x[ai-1],y[ai],x[ai],yc)
    # before
    bis=im-(y[im::-1]<ym*frac).nonzero()[0]
    if len(bis)==0:
        bi=0
    else:
        bi=min(bis[0],len(x)-2)
    b=line_two_points(y[bi],x[bi],y[bi+1],x[bi+1],yc)
    return b,a

def peak_crossings(x,y,frac=0.5,axis=None,ym=None):
    if axis is None:
        axis=last_axis(x)
    if ym is None:
        return eval_iterated(lambda x,y:peak_crossings_1D(x,y,frac),(x,y),vec_dims=[axis])
    else:
        return eval_iterated(lambda x,y,ym:peak_crossings_1D(x,y,frac,ym),(x,y,ym),vec_dims=[axis])
    
def fwhm(x,y,axis=None):
    x1,x2=peak_crossings(x,y,0.5,axis)
    return x2-x1
    
def find_peaks_iter_rmv(y,n,Dy_thresh=0,max_half_int=float('inf'),cyclic=False,min_half_int=-float('inf')):
    """Finds peaks using 'iterative removal'.
    
    The maximum value is recorded as a peak. Then, an interval
    around this maximum is removed. The interval is defined by the closest local
    minima or max_half_int, whichever is smaller. Local minima are defined by
    y rising from the minimum by Dy_thresh.
    Args:
        y (sequence): vector in which to find peaks
        n (int): number of peaks
        Dy_thresh (float): Minimum increase to declare a local minimum
        max_half_int (float): maximum distance from peak for removal
        cyclic (bool): cyclic boundary conditions
    Returns: the peaks in order of discovery.   
        """
    y=y.copy() # we change it
    min_y=y.min() # set 'removed' intervals to this
    def find_rmv_peak():
        ind_peak=y.argmax()
        def scan(ind,dir): 
            if cyclic:
                stop_ind=None
            else:
                if dir>0:
                    stop_ind=len(y)-1
                else:
                    stop_ind=0    
            scan_min_y=y[ind]
            scan_min_ind=ind
            dist=0
            halt=False
            while ind!=stop_ind:
                # Have we risen out of a minimum?
                if y[ind+dir]-scan_min_y>Dy_thresh:
                    halt=True
                if dist>=min_half_int and halt:
                    break
                if dist==max_half_int:
                    break
                ind+=dir
                dist+=1
                # Update minimum
                if y[ind]<scan_min_y:
                    scan_min_y=y[ind]
                    scan_min_ind=ind
            return scan_min_ind
        # Set interval to minimum
        left_ind=scan(ind_peak,-1)
        right_ind=scan(ind_peak,1)
        y[left_ind:right_ind+1]=min_y
        return ind_peak
    ind_peaks=[]
    for _ in range(n):
        ind_peaks.append(find_rmv_peak())
    return ind_peaks
                  
def log10_bounded(x):
    """log10 with non-positive values set to lowest positive value"""
    x=np.array(x)
    xe0=x<=0
    x[xe0]=abs(x[~xe0]).min()
    return np.log10(x)
    
def converge_aitken_series(f, n_start=0, f_startm1=0,eps=1e-6,max_iter=-1,min_consec=2):
    """Finds the limit of a series using Aitken acceleration
    an = converge_aitken_series(f, n_start, f_startm1)
    where f(n, fp) returns the nth member of the sequence given the n-1th
    member e.g. to sum series s_n, f = s_n + fp.
    n_start is the first value of n (default 1), f_startm1 is the value of fp
    passed at the start (default 0).
    Args:
        min_consec (int): number of consecutive iterations error must be below eps
            to terminate (for robustness)
    """
    def aitken(x1, x2, x3):
        x1,x2,x3=np.asarray(x1),np.asarray(x2),np.asarray(x3)
        a = x1 - (x2 - x1)**2/(x3 - 2*x2 + x1)
        a=np.asarray(a)
        inds = np.isnan(a)
        a[inds] = x3[inds]
        inds=np.isinf(a)
        a[inds]=x3[inds]
        return a
    
    n=n_start
    fnp0=f(n+0,f_startm1)
    fnp1=f(n + 1, fnp0)
    fnp2 = f(n + 2, fnp1)
    an = aitken(fnp0, fnp1, fnp2)
    num_consec=0
    while n!=max_iter:
        n+=1
        anm1 = an
        fnp0 = fnp1
        fnp1 = fnp2
        fnp2 = f(n + 2, fnp1)
        an = aitken(fnp0, fnp1, fnp2)
        err = np.asarray((an - anm1)/an)
        anz=an==0 # Special case for an=0
        err[anz]=an[anz]-anm1[anz]
        if abs(err).max()<eps:
            num_consec+=1
        else:
            num_consec=0
        if num_consec==min_consec:
            break
    return an

def divide0(a,b,result=0):
    """Division with quotient=result when divisor is zero.
    http://stackoverflow.com/questions/26248654/numpy-return-0-with-divide-by-zero
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.asarray(np.true_divide( a, b ))
        c[ ~ np.isfinite( c )] = result  # -inf inf NaN
    return c
    
def round_to_multiple(x,a):
    """Round x to nearest multiple of a"""
    return a*np.round(x/a)

def round_to_odd_multiple(x,a):
    return a*(2*round((x-a)/(2*a))+1)
    
def slowing(k,a=1):
    """Identity function except it varies slowly around k=0.
    
    The parameter a is the scale over which the slowdown occurs:
        slowing(a,a)=a/2
    """
    return k/(a**2*divide0(1,k**2)+1)  
    
def moment(x,f,n,nrm_fac=None,axis=None):
    """sum[x^n*f]/nrm_fac
    nrm_fac defaults to sum(f)."""
    if nrm_fac is None:
        nrm_fac=f.sum(axis,keepdims=True)
    return squeeze_leading(divide0((x**n*f).sum(axis,keepdims=True),nrm_fac))
    
def moment2(x,y,f,nx,ny,nrm_fac=None):
    """sum[x^nx*y^ny*f]/nrm_fac"""
    if nrm_fac is None:
        nrm_fac=f.sum()
    return (x**nx*y**ny*f).sum()/nrm_fac
    
def mean_and_variance2(x,y,f):
    """2D mean and variance calculation.
    
    The arguments must be broadcastable.
    
    Returns:
        tuple: <x>,<y>,<(x-<x>)^2>,<(y-<y>)^2>,<(x-<x>)(y-<y>)>
    """
    nrm_fac=f.sum()
    mx=moment(x,f,1,nrm_fac=nrm_fac)
    my=moment(y,f,1,nrm_fac=nrm_fac)
    xp=x-mx
    yp=y-my
    vxx=moment(xp,f,2,nrm_fac)
    vyy=moment(yp,f,2,nrm_fac)
    vxy=moment2(xp,yp,f,1,1,nrm_fac)
    return mx,my,vxx,vyy,vxy

def diagonalize_2d_covariance(vx2,vy2,vxy):
    """Diagonalize 2D covariance matrix to find principle axes.
    Returns:
        tuple (major,minor,theta): major and minor principle root-mean-square
            lengths, and angle of major axis to x axis.
    """
    # Off-diagonal entries of intertia tensor are negative 
    m=np.array([[vx2,vxy],[vxy,vy2]])
    vals,vecs=np.linalg.eig(m)
    order=np.argsort(vals)
    min,maj=vals[order]**0.5
    vecs=vecs[:,order]
    theta=np.arctan2(vecs[1,1],vecs[0,1])
    return maj,min,theta

def mean_and_std(x,f):
    nrm_fac=sum(f)
    mu=moment(x,f,1,nrm_fac=nrm_fac)
    sigma=moment(x-mu,f,2,nrm_fac)**0.5
    return mu,sigma
    
def thresholded(y,fraction_max=None,level=None):
    if level is not None:
        assert fraction_max is None
    else:
        level=y.max()*fraction_max
    y=y.copy()
    y[y<level]=0
    return y
    
def mean(iterable):
    """x can be any iterable"""
    iterator=iter(iterable)
    value=next(iterator)
    num=1
    for element in iterator:
        num+=1
        # value+=element fails when numpy broadcasting
        value=value+element
    return value/num
    
def interpolating_matrix(f,n):
    """Compute matrix representing interpolation given interpolation function.
    
    The interpolation problem is to resample (x,y) to the points xi producing yi.
    This function takes an existing interpolation method and represents it as a
    matrix M such that yi=M*y. This works provided the method is linear. Nearest
    neighbour, linear interpolation and spline interpolation all fall into this 
    category.
    
    Args:
        f (function): y->yi
        n: length of x
    """
    def column(j):
        y=np.zeros(n)
        y[j]=1
        yi=f(y)
        return yi
    yi=np.array([column(j) for j in range(n)]).T
    return yi
    
def gegenbauer(alpha,n,x):
    """Return nth order Gegenbauer polynomial with weight function (1-x**2)**(alpha-0.5).
    
    The difference between this and scipy.special.gegenbauer is that here one
    passes the value for which the polynomial is evaluated. This makes it compatible
    with sympy.
    """
    if n==0:
        return 1
    elif n==1:
        return 2*alpha*x
    else:
        return (2*x*(n+alpha-1)*gegenbauer(alpha,n-1,x)-(n+2*alpha-2)*gegenbauer(alpha,n-2,x))/n
        
def xcorr_fft_2d(a,b,a_ft=False,b_ft=False,shift=True):
    """Compute cross-correlation between two 2D arrays of equal shape by using fourier transform 
    (uses convolution theorem with an extra conjugate).
    Can supply pre-calculated fts of a and/or b. If so, set a_ft and/or b_ft to True"""
    if a.shape != b.shape:
        raise ValueError('Both input arrays must have the same shape - got {0} and {1}.'.format(a.shape,b.shape))
    afft = (a if a_ft else np.fft.fft2(a))
    bfft = (b if b_ft else np.fft.fft2(b))
    xc =  np.fft.ifft2( afft * np.conj(bfft) ) 
    if shift:
        xc = np.fft.fftshift(xc)
    return xc
    
def xcorr_fft_1d(a,b,a_ft=False,b_ft=False,shift=True):
    """Compute cross-correlation between two 1D arrays of equal shape by using fourier transform 
    (uses convolution theorem with an extra conjugate).
    Can supply pre-calculated fts of a and/or b. If so, set a_ft and/or b_ft to True"""
    if a.shape != b.shape:
        raise ValueError('Both input arrays must have the same shape - got {0} and {1}.'.format(a.shape,b.shape))
    afft = (a if a_ft else np.fft.fft(a))
    bfft = (b if b_ft else np.fft.fft(b))
    xc =  np.fft.ifft( afft * np.conj(bfft) ) 
    if shift:
        xc = np.fft.fftshift(xc)
    return xc

def allclose(a,b,atol_frac=1e-5,rtol=1e-5,atol=1e-8,equal_nan=False):
    nones=sum(x is None for x in (a,b))
    if nones==2:
        return True
    elif nones==1:
        return False
    atol=max(atol,max(np.max(a),np.max(b))*atol_frac)
    return np.allclose(a,b,rtol=rtol,atol=atol,equal_nan=equal_nan)

def multiply_and_sum(factors,axes,keepdims=False):
    """Equivalent to sum(factors[0]*factors[1]*...,axes,keepdims=keeepdims)."""
    if not isinstance(axes,tuple):
        axes=(axes,)
    assert np.all(axis<0 for axis in axes)
    assert all(np.ndim(factor)<=26 for factor in factors)
    def make_str(ndim):
        return ''.join(chr(ord('z')+1-ndim+n) for n in range(ndim))
    input_subscripts=','.join(make_str(np.ndim(factor)) for factor in factors)
    output_subscripts=''.join(chr(ord('z')+1+n) for n in range(-max(np.ndim(factor) for factor in factors),0) if n not in axes)
    subscripts=input_subscripts+'->'+output_subscripts
    output=np.einsum(subscripts,*factors)
    if keepdims:
        for axis in sorted(axes,reverse=True):
            output=np.expand_dims(output,axis)
    return output
    
def crop_vector_to_axis(x,y,xlims):
    f = (x<xlims[1]) * (x > xlims [0])
    x,y=x[f],y[f]
    return x,y
