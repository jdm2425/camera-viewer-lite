import heapq
import numpy as np
from scipy.optimize import minimize
import fourier as ft
from . import wrap_to_pm

def optimal_linear_phase(x,y):
    """Linear phase (translation in conjugate space) for least squares field agreement.
    
    For two fields f and g sampled at x, optimal_linear_phase(x,f*conj(g)) returns
    k_opt such that f'=f*exp(-j*k_opt*x) is least-squares closest to g, up to an arbitrary
    absolute phase.
    
    For one field f, optimal_linear_phase(x,f*abs(f)) returns k such at f'
    is least-squares closest to its transform limit.

    Args:
        x (1D array): sample points
        y (1D array): f*conj(g) for agreement between f and g, f*abs(f) for
            best overlap with delta function at origin (in conjugate domain)
    Returns:
        tuple: k_opt, the optimal linear phase, and phi_opt, the optimal zeroth order phase
    """
    deltax=x[1]-x[0]
    k=ft.conj_axis(x)
    yk=ft.trans(x,-1,y,k)
    ind_0=abs(yk).argmax()
    def dft(k):
        return (y*np.exp(-1j*k*x)).sum()
    k_scale=abs(k[1]-k[0])
    def fun(k_scaled):
        return -abs(dft(k_scaled*k_scale))
    k_opt=minimize(fun,k[ind_0]/k_scale).x[0]*k_scale
    phi_opt=np.angle(dft(k_opt))
    return k_opt,phi_opt
    
def apply_linear_phase(x,f,g):
    k_opt=optimal_linear_phase(x,f*g.conj())[0]
    fp=f*np.exp(-1j*k_opt*x)
    return fp
    
def apply_straight_line_phase(x,f,g):
    """Adjust linear phase to best match reference."""
    fp=apply_linear_phase(x,f,g)
    return fp*np.exp(-1j*np.angle((fp*g.conj()).sum()))
    
def apply_straight_line_phase_scale(x,f,g):
    """Apply scaling and linear and absolute phase to minimize field error.
    
    Args:
        x (1D array): sampling points
        f (1D array): field to be adjusted
        g (1D array): reference field
    
    Returns:
        1D array: f scaled and phase shifted for least squares difference to g
    """
    fp=apply_linear_phase(x,f,g)
    a=(g*fp.conj()).sum()/(fp*fp.conj()).sum()
    return fp*a

def unwrap_axes(phi,raveled_index,axes,all_axes=False):
    """Works along axes in specified order."""
    # We work with negative axis indices only.
    assert all(axis<0 for axis in axes)
    if all_axes:
        # If an axis wasn't listed in axes, append it.
        axes=list(axes)
        for n in range(-phi.ndim,0):
            if n not in axes:
                axes.append(n)
    index=np.unravel_index(raveled_index,phi.shape)
    phi_index_orig=phi[index]
    phi_to_unwrap=phi
    for axis in axes:
        phi_unwrapped=np.unwrap(phi_to_unwrap,axis=axis)
        phi+=2*np.pi*np.round((phi_unwrapped-phi_to_unwrap)/(2*np.pi))
        # phi is now consistent with phi_unwrapped. Pick out index along the axis
        # we just unwrapped, and repeat
        phi_to_unwrap=phi_unwrapped.take([index[axis]],axis)
    phi+=2*np.pi*np.round((phi_index_orig-phi[index])/(2*np.pi))
    return phi

def unwrap_paint_fill(phi,w):
    """
    w and phi are modified
    Args:
        phi:
        w:

    Returns:

    """
    phi=np.asarray(phi)
    w=np.asarray(w)
    assert phi.shape==w.shape
    shape=phi.shape
    inds=np.unravel_index(w.argmax(),shape)
    boundary_heap=[(-w[inds],inds,None)]
    done=0
    while len(boundary_heap)>0:
        _,inds,prev_inds=heapq.heappop(boundary_heap)
        if prev_inds is not None:
            # Unwrap by placing phi[inds] on the same level of the Reimann surface
            # as phi[prev_inds]
            phi[inds]+=2*np.pi*round((phi[prev_inds]-phi[inds])/(2*np.pi))
        x=np.isnan(w).sum()
        done+=1
        if not (done%10000):
            print(done,'of',w.size)
        for axis in range(phi.ndim):
            for dir in (-1,1):
                check_inds=list(inds)
                check_inds[axis]+=dir
                check_inds=tuple(check_inds)
                # Is index valid and not unwrapped yet?
                if (0<=check_inds[axis]<shape[axis]) and not np.isnan(w[check_inds]):
                    entry=-w[check_inds],check_inds,inds
                    heapq.heappush(boundary_heap,entry)
                    w[check_inds]=np.nan
                    # # Is it not already in the boundary?
                    # if inds not in not any(entry[1]==e[1] for e in boundary):
    
