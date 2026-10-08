import numpy as np
import mathx

def array(**kwargs):
    """
    Args:
        axis: dimension
        zero: first element
        last: last element
        delta: spacing
        N: number of samples
    
    Returns:
        numpy.ndarray
    """
    axis=kwargs.pop('axis',-1)
    if 'vector' in kwargs:
        a=mathx.reshape_vec(kwargs.pop('vector'),axis)
    elif 'array' in kwargs:
        a=kwargs.pop('array')
    else:
        if all(k in kwargs for k in('zero','N','delta')):
            zero=np.array(kwargs.pop('zero'))
            N=kwargs.pop('N')
            delta=np.array(kwargs.pop('delta'))
        elif all(k in kwargs for k in ('zero','last','delta')):
            zero=np.array(kwargs.pop('zero'))
            last=np.array(kwargs.pop('last'))
            delta=kwargs.pop('delta')
            N=set(round((last-zero)/delta).flatten().tolist())
            if len(N)!=1:
                raise ValueError('N must be same for all sub-vectors')
            N=N.pop()
        elif all(k in kwargs for k in('zero','N','last')):
            zero=np.array(kwargs.pop('zero',0))
            last=np.array(kwargs.pop('last'))
            N=kwargs.pop('N')
            delta=(last-zero)/(N-1)
        else:
            raise ValueError('Unknown argument combination '+str(list(kwargs.keys())))
        a=zero+mathx.reshape_vec(np.arange(N),axis)*delta
    if len(kwargs)>0:
        raise ValueError('Unused arguments '+str(list(kwargs.keys())))
    return a
    
def kwargs(v,axis=None):
    if axis is None:
        axis=get_axis(v)
    return {'axis':axis,'zero':zero(v,axis),'delta':delta(v,axis),'N':v.shape[axis]}
    
def get_axis(v):
    nsd=[n for n,s in enumerate(v.shape) if s>1]
    if len(nsd)>1:
        raise ValueError('More than one non-singleton dimension')
    return nsd[0]-v.ndim

def delta(v,axis=None):
    if axis is None:
        axis=get_axis(v)
    r=v.take([1],axis)-v.take([0],axis)
    if r.size==1:
        r=np.asarray(r).item()
    return r
    
def zero(v,axis=None):
    if axis is None:
        axis=get_axis(v)
    r=v.take([0],axis)
    if r.size==1:
        r=np.asarray(r).item()
    return r
    
def is_usv(v,axis=None):
    v=np.asarray(v)
    if axis is None:
        nsd=[n for n,s in enumerate(v.shape) if s>1]
        if len(nsd)!=1:
            return False
        axis=nsd[0]-v.ndim
    delta=np.diff(v,axis=axis)
    return np.allclose(delta,delta.take([0],axis))
    
def desc(v,axis=None,zero_fmt='%g',delta_fmt='%g'):
    v=np.asarray(v)
    if axis is None:
        axis=get_axis(v)
    return 'z'+zero_fmt%zero(v,axis)+'d'+delta_fmt%delta(v,axis)+'N%d'%v.shape[axis]
    
def pad(v,b,a,axis=None):
    if axis is None:
        axis=get_axis(v)
    l=np.shape(v)[axis]
    vp=mathx.reshape_vec(np.arange(-b,l+a),axis)*delta(v,axis)+zero(v,axis)
    return vp
    
def pad_sampled(v,f,b,a,axis=None,value=0):
    f=np.asarray(f)
    if axis is None:
        axis=get_axis(v)
    shape_a=list(f.shape)
    shape_a[axis]=a
    shape_b=list(f.shape)
    shape_b[axis]=b
    fp=np.concatenate((value*np.ones(shape_b),f,value*np.ones(shape_a)),axis)
    vp=mathx.reshape_vec(np.arange(-b,f.shape[axis]+a),axis)*delta(v,axis)+zero(v,axis)
    return vp,fp

def pad_sampled_multi(vs,f,bas):
    """Pad a function of multiple USVs.
    """
    vps=[]
    for v,ba in zip(vs,bas):
        vp,f=pad_sampled(v,f,*ba)
        vps.append(vp)
    return vps,f
    
def interp1d(x,y,xi,axis=None,extrap=True):
    """
    Args:
        x (uniformly sampled vector/array): sampled x values
        y (array): sampled y values
        xi (array): x values to interpolate onto
        axis (int): axis along which to interpolate.
        extrap (bool): if True, use linear extrapolation based on the extreme values.
            If false, nearest neighbour is used for extrapolation instead.
    """
    x=np.asarray(x)
    if axis is None:
        axis=get_axis(x)
    return mathx.interp1d_lin_reg(zero(x,axis),delta(x,axis),y,xi,axis,extrap)

def interp1d_multi(x,ys,xi,axis=None,extrap=True):
    """Like interp1d but is a generator that iterates over arrays.

    Args:
        x (uniformly sampled vector/array): sampled x values
        ys (series of arrays): sampled y values
        xi (array): x values to interpolate onto
        axis (int): axis along which to interpolate.
        extrap (bool): if True, use linear extrapolation based on the extreme values.
            If false, nearest neighbour is used for extrapolation instead.
    """
    x=np.asarray(x)
    if axis is None:
        axis=get_axis(x)
    interp=mathx.Interp1DUniform(zero(x,axis),delta(x,axis),x.shape[axis],axis,xi,extrap)
    for y in ys:
        yield interp(y)
    
def interp2d(x,y,z,xi,yi):
    """
    x & y must be 1D. z must be x.size*y.size
    """
    x0=x[0]
    y0=y[0]
    Dx=x[1]-x[0]
    Dy=y[1]-y[0]
    Nx=len(x)
    Ny=len(y)
    nx=np.clip(np.floor((xi-x0)/Dx).astype(int),0,Nx-2)
    ny=np.clip(np.floor((yi-y0)/Dy).astype(int),0,Ny-2)
    z00=z[nx,ny]
    z01=z[nx,ny+1]
    z10=z[nx+1,ny]
    z11=z[nx+1,ny+1]
    dx=(xi-(nx*Dx+x0))/Dx
    dy=(yi-(ny*Dy+y0))/Dy
    zi=(1-dx)*(1-dy)*z00+(1-dx)*dy*z01+dx*(1-dy)*z10+dx*dy*z11
    return zi
    
def get_frac_ind(x,xp,axis=None,clip=False):
    """Get fractional indices (linear interpolation) into uniformly-sampled array.
    
    Args:
        x (uniformly sampled vector/array): indices are returned into this
        xp (array): x values of which to return fractional indices
    
    Returns:
        array of fractional indices
    """
    x=np.asarray(x)
    xp=np.asarray(xp)
    if axis is None:
        axis=get_axis(x)
    xixp=(xp-zero(x,axis))/delta(x,axis)
    #xixp=interp1d(x,mathx.reshape_vec(range(0,x.shape[axis]),axis),xp,axis)
    if clip:
        xixp=np.clip(xixp,0,x.shape[axis]-1)
    return xixp
    
def differentiate(x,y,n=1,axis=None):
    x=np.asarray(x)
    if axis is None:
        axis=get_axis(x)
    assert x.shape[axis]==np.shape(y)[axis]
    return mathx.diff(y,n,axis)/delta(x,axis)**n
    
def crop_slice(x,x1,x2,clip=True,axis=None,step=None):
    """Slice which crops a USV to a range.
    Args:
        x (array-like): USV to crop
        x1,x2 (scalars): interval to crop to (sorted)
        clip (bool): if True, restricts indices to valid range
        axis (int): axis to work along, inferred from x if None
        step (int): step for returned slice object
    Returns: slice object"""
    if axis is None:
        axis=get_axis(x)
    inds=get_frac_ind(x,(x1,x2)).round().astype(int)
    if clip:
        inds.clip(0,len(x)-1,inds)
    return slice(inds[0],inds[1]+1,step)
    
def crop1d(x,x1,x2,y=None,clip=True,axis=None,step=None):
    if y is None:
        y=x
    slc=crop_slice(x,x1,x2,clip,axis,step)
    return y[slc]
    
# class CubicHermiteInterpolator:
#     """Interpolate from uniformly sampled data using cubic Hermite polynomial.
#     A port of my interp1_uni2arb_spline_bsx  family of functions in MATLAB. Got half
#     way through before I realised that I don't need it.
#     """
#     def __init__(self,x,xi,extrap_before='nearest',extrap_after='nearest',axis=None):
#         if axis is None:
#             axis=get_axis(x)
#         assert extrap_before in ('nearest','linear')
#         assert extrap_after in ('nearest','linear')
#         N=x.shape[axis]
#         x0=zero(x,axis)
#         deltax=delta(x,axis)
#         f=(xi-x0)/deltax
#         n=np.clip(np.floor(x).astype(int),-1,-3)
#         xn=x0+n*deltax
#         t=(xi-xn)/deltax
#         if extrap_before is 'nearest':
#             t=np.maximum(t,0)
#         if extrap_after is 'nearest':
#             t=np.minimum(t,1)
#         
#         t2=t**2
#         t3=t**3
#         # Evaluate basis functions
#         h00=2*t3-3*t2+1
#         h10=t3-2*t2+t
#         h01=-2*t3+3*t2
#         h11=t3-t2
#         
#         if extrap_before is 'linear':
#             tlt0=t<0 # t less than zero
#             h00[tlt0]=1
#             h10[tlt0]=t[tlt0]
#             h01[tlt0]=0
#             h11[tlt0]=0
#             
#         if extrap_after is 'linear':
#             tgt1=t>1 # t greater than 1
#             h00[tgt1]=0
#             h10[tgt1]=0
#             h01[tgt1]=1
#             h11[tgt1]=t[tgt1]-1
#             
#         self.axis=axis
#         self.n=n
#         self.h=[[h00,h01],[h10,h11]]
#         self.y_shape=None
#         
#     def set_y_shape(self,shape):
#         self.n_unraveled=np.unravel_index(self.n,shape)
#         self.np1_unraveled=np.unravel_index(self.n+1,shape)
#         
#     def __call__(self,y):
        
        
      
# def integrate_spline(x,y,axis):
#     if axis is None:
#         axis=get_axis(x)
#     N=y.shape[axis]
#     deltax=delta(x)
#     ynm2=mathx.slice_dim(
#     yn=y
#     
#     
#     
# % x_n = x(n)
# % x_n = x_1 + (n-1)*Dx
# N = size(x, dim);
# Dx = index_dim_bsx(x, 2, dim) - index_dim_bsx(x, 1, dim);
# 
# y_n = y;
# y_nm2 = index_dim_bsx(y, makecol([1, 1, 1:N-2], dim), dim);
# y_nm1 = index_dim_bsx(y, makecol([1, 1:N-1], dim), dim);
# y_np1 = index_dim_bsx(y, makecol([2:N, N], dim), dim);
# y_1 = index_dim_bsx(y, 1, dim);
# y_2 = index_dim_bsx(y, 2, dim);
# y_Nm1 = index_dim_bsx(y, N-1, dim);
# y_N = index_dim_bsx(y, N, dim);  
# ycd_n = (y_np1 - y_nm1)/2;
# ycd_n = subassign_dim_bsx(ycd_n, makecol([1 N], dim), dim, cat(dim, y_2 - y_1, y_N - y_Nm1));
# ycd_nm1 = index_dim_bsx(ycd_n, makecol([1, 1:N-1], dim), dim);
# %Y = cumsum(Dx*(1/2*y_nm1 + 1/12*ycd_nm1 + 1/2*y_n - 1/12*ycd_n));
# Y=cumsum(btimes(Dx,1/2*y_nm1 + 1/12*ycd_nm1 + 1/2*y_n - 1/12*ycd_n),dim);
# Y = bsxfun(@minus, Y, indexDim2(Y, dim, 1));
#     
