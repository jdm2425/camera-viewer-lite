import logging
import numpy as np
from . import *
logger=logging.getLogger(__name__)

def index(array,indices,axis):
    """Take elements from array along axis if it is spanned.
    
    If array spans axis (i.e. array.shape[axis] is valid >1) then returns
    array.take(indices,axis); otherwise returns array. Can be thought of as
    indexing with broadcasting semantics.
    """
    array=np.asarray(array)
    indices=np.asarray(indices)
    if -array.ndim<=axis<array.ndim:
        if array.shape[axis]>1:
            return array.take(indices,axis)
        else:
            # take can remove dimension or add dimensions - need to mimic this
            return array.take(np.zeros(np.ones(indices.ndim,int),int),axis)
    else:
        return array
        
def index_multi(array,indss,axes):
    axis_inds_srtd=np.argsort(axes)
    indss=np.asarray(indss)[axis_inds_srtd]
    axes=np.asarray(axes)[axis_inds_srtd]
    for ind,axis in zip(indss,axes):
        array=index(array,ind,axis)
    return array

def axis_len_broadcast(array,axis):
    """Effective length along given axis under broadcasting rules."""
    array=np.asarray(array)
    if axis<-array.ndim:
        return 1
    elif axis<array.ndim:
        return array.shape[axis]
    raise ValueError('axis %d too large for array of shape %s'%(axis,array.shape))

def slice_dim(slc,axis):
    """Return slice object that indexes along an arbitrary axis.
    Args:
        slc: the object used for slicing e.g. a slice object, an int or a sequence
        axis: the axis to slice
    """
    if axis<0:
        return [Ellipsis,slc]+[slice(None)]*(-axis-1)
    else:
        return [slice(None)]*axis+[slc,Ellipsis]
        
def slice_dims(slcs,dims):
    """List of slices with slices at given positions and : everywhere else."""
    dims=np.array(dims)
    if np.all(dims<0):
        n=-dims.min()
        l=[Ellipsis]+[slice(None)]*n
    elif np.all(dims>=0):
        n=dims.max()
        l=[slice(None)]*n+[Ellipsis] # not sure the trailing Ellipsis is necessary
    else:
        raise ValueError('All dims must have same sign')
    for dim,slc in zip(dims,slcs):
        l[dim]=slc
    return l

def take(array,inds,axis):
    """Like numpy take, but accepts slice object as well."""
    return array[slice_dim(inds,axis)]

def concatenate(arrays,axis):
    """Concatenate along axis.

    Differs from numpy.concatenate in that it works if the axis doesn't exist.
    """
    logger.debug('Applying asarray to each element of arrays.')
    arrays=[np.asarray(array) for array in arrays]
    logger.debug('Adding axes to each element of arrays as necessary')
    if axis>=0:
        arrays=[array[[Ellipsis]+[None]*max(axis-array.ndim+1,0)] for array in arrays]
    else:
        arrays=[array[[None]*max(-axis-array.ndim,0)+[Ellipsis]] for array in arrays]
    logger.debug('Calling numpy.concatenate')
    return np.concatenate(arrays,axis)
    
def iterate_broadcast_op(f,xs,axis,chunk_len=1,print_prog=False):
    """
    Gotchas: broadcasts all xs against one another, which can make calculations
    slow."""
    xs=np.broadcast_arrays(*xs)
    N=xs[0].shape[axis]
    ns=range(0,N,chunk_len)
    if print_prog:
        print(str(N)+' iterations:',end=' ',flush=True)
    for n in ns:
        if print_prog:
            print(n,end= ' ',flush=True)
        inds=np.arange(n,min(n+chunk_len,N))
        xps=[np.take(x,inds,axis) for x in xs]    
        yp=f(*xps)
        if n==0:
            shape=list((1,)*(max(-axis,0)-yp.ndim)+yp.shape)
            shape[axis]=N
            y=np.zeros(shape,dtype=yp.dtype)
        y[slice_dim(inds,axis)]=yp
    if print_prog:
        print('Done')
    return y
    
def iterate_broadcast_op_multi(f,xs,axes,print_prog=False):
    axes=np.array(axes)
    if not (all(axes>=0) or all(axes<0)):
        raise ValueError('All axes must be negative or non-negative') 
    xs=np.broadcast_arrays(*xs)
    subshape=np.array(xs[0].shape)[axes]
    N=subshape.prod()
    if print_prog:
        print(str(N)+' iterations:',end=' ')
    for n in range(N):
        if print_prog:
            print(n,end=' ')
        inds=np.unravel_index(n,subshape)
        # We need to index without losing a dimension. See numpy's rules
        # for basic indexing
        slc=slice_dims([slice(ind,ind+1) for ind in inds],axes)
        xps=[x[slc] for x in xs]
        yp=f(*xps)
        if n==0:
            if axes[0]>0:
                shape=yp.shape+(1,)*max(max(axes)-yp.ndim,0)
            else:
                shape=(1,)*max(max(-axes)-yp.ndim,0)+yp.shape
            shape=np.array(shape)
            if not all(shape[axes]==1):
                raise ValueError('Size of function return value along iteration dimensions must be 1')
            shape[axes]=subshape
            y=np.zeros(shape,dtype=yp.dtype)
        y[slc]=yp
    if print_prog:
        print('Done')
    return y
    
def vectorize(f,vec_dims=None,iter_dims=None,keep_iter_dims=False):
    def vectorized_f(*args):
        eval_iterated(f,args,vec_dims,iter_dims,keep_iter_dims)
    return vectorized_f
    
def subarrays(arrays,iteration_axes=None,subarray_axes=None):
    """Generator function for iterating over arbitrary axes of multiple arrays.

    The returned arrays are views of the originals, so assignment is possible e.g.
    using subarray[:]=x notation. 
    
    The arrays need only be mutually broadcastable along iteration_axes.
    
    Only one of iteration_axes or subarray_axes need to be specified as their union
    is all axes spanned by arrays.
    
    Args:
        arrays: list of arrays to iterate over
        iteration_axes: list of axes (negative integers) to iterate over
        subarray_axes: list of axes (negative integers) which the subarrays will
            possess
    """
    arrays=[np.asarray(array) for array in arrays]
    # Number of dimensions of broadcast arrays
    ndim=max(array.ndim for array in arrays)
    # Work out vectorized and iterated dimensions
    if subarray_axes is None:
        subarray_axes=[n for n in range(-ndim,0) if n not in iteration_axes]
    elif iteration_axes is None:
        iteration_axes=[n for n in range(-ndim,0) if n not in subarray_axes]
    else:
        raise ValueError('Must specify either subarray_axes or iteration_axes')
    # Must be lists for numpy indexing
    iteration_axes=list(iteration_axes)
    subarray_axes=list(subarray_axes)
    # Union of iteration_axes and subarray_axes must be all dimensions
    assert set(subarray_axes).union(iteration_axes)==set(range(-ndim,0))
    if len(iteration_axes)==0:
        yield arrays
        return
    def get_axis_len(axis):
        """Length along axis of broadcast arrays.
        We use this function instead of the numpy broadcasting functions because
        the arrays only have to be broadcastable along iteration_axes."""
        ls=[axis_len_broadcast(array,axis) for array in arrays]
        assert all((ls[0]==l or ls[0]==1 or l==1) for l in ls),'Lengths of arrays along axis %d are %s but they should be broadcastable'%(axis,str(ls))
        return max(ls)
    # 1D array of the dimensions to iterate over
    iteration_shape=np.asarray([get_axis_len(axis) for axis in iteration_axes])
    for n in range(iteration_shape.prod()):
        # Indices along iteration axes
        indices=np.unravel_index(n,iteration_shape)
        # Get suitable subarrays of arrays
        def index_array(array):
            if array.ndim==0:
                return array
            index_obj=[slice(None),]*array.ndim
            for axis,index in zip(iteration_axes,indices):
                if axis<-array.ndim:
                    continue
                if array.shape[axis]==1:
                    continue
                index_obj[axis]=slice(index,index+1)
            return array[index_obj]
            # if keep_iteration_axes:
            #     indices_multi=[[index] for index in indices]
            # else:
            #     indices_multi=indices
            # return index_multi(array,indices_multi,iteration_axes)
        arrays_indexed=[index_array(array) for array in arrays]
        # if broadcast_arrays:
        #     arrays_indexed=np.broadcast_arrays(*arrays_indexed)
        yield arrays_indexed

def eval_iterated(f,xs,vec_dims=None,iter_dims=None,keep_iter_dims=False,print_progress=False,broadcast_xs=False,
                  iter_chunk_size=1):
    """General purpose solution to making functions broadcast their arguments. 
    vec_dims and iter_dims are sequences of negative axes.
    Must specify one or both of vec_dims and iter_dims. Their union is all dims. If both are specified then
    they must cover all dims. vec_dims and iter_dims divide the broadcasted arguments index space into two subspaces.
    The vec_dims subspace is retained in the arguments xs and passed to func, while the iter_dims subspace is iterated over.
    If broadcast_xs is True, then xs are broadcast against one another (with
    np.broadcast arrays) before being passed to f.
    f returns a sequence of values
    """
    if iter_chunk_size!=1:
        assert keep_iter_dims
    # Number of dimensions of broadcast xs
    ndim_xs=max(np.ndim(x) for x in xs)
    # Work out vectorized and iterated dimensions
    if vec_dims is None:
        vec_dims=[n for n in range(-ndim_xs,0) if n not in iter_dims]
    elif iter_dims is None:
        iter_dims=[n for n in range(-ndim_xs,0) if n not in vec_dims]
    else:
        raise ValueError('Must specify either vec_dims or iter_dims')
    # Must be lists for numpy indexing
    iter_dims=list(iter_dims)
    vec_dims=list(vec_dims)
    # Union of iter_dims and vec_dims must be all dimensions
    assert set(vec_dims).union(iter_dims)==set(range(-ndim_xs,0))
    if len(iter_dims)==0:
        return f(*xs)
    def get_axis_len(axis):
        ls=[axis_len_broadcast(x,axis) for x in xs]
        assert all((ls[0]==l or ls[0]==1 or l==1) for l in ls),'Lengths of xs along axis %d are %s but they should be broadcastable'%(axis,str(ls))
        return max(ls)
    iter_shape=np.asarray([get_axis_len(dim) for dim in iter_dims])
    iter_shape_chunks=np.ceil(iter_shape/iter_chunk_size).astype(int)
    if print_progress:
        print('Starting ',iter_shape_chunks.prod(), ' iterations:',end='')
    for n in range(iter_shape_chunks.prod()):
        if print_progress:
            print(n,' ',end='',flush=True)

        # Convert scalar 'raveled' index into unraveled indices along the iterated dimensions.
        iter_inds=np.unravel_index(n,iter_shape_chunks)

        # Index the function arguments.
        if keep_iter_dims:
            #inds=[[ind] for ind in iter_inds]
            #slices=[slice(ind*iter_chunk_size,ind+iter_chunk_size) for ind in iter_inds]
            inds=[range(ind*iter_chunk_size,min((ind+1)*iter_chunk_size,size)) for (ind,size) in zip(iter_inds,iter_shape)]
            xps=[index_multi(x,inds,iter_dims) for x in xs]
        else:
            xps=[index_multi(x,iter_inds,iter_dims) for x in xs]

        if broadcast_xs:
            xps=np.broadcast_arrays(*xps)

        # Evaluate the function with indexed arguments.
        yps=f(*xps)

        # For n=0, need to generate empty arrays for y.
        if n==0:
            ys=[]           
            for yp in yps:
                yp=np.array(yp)
                if keep_iter_dims:
                    y_shape=np.array((1,)*(-min(iter_dims)-yp.ndim)+yp.shape,dtype=int)
                    #if not all(y_shape[iter_dims]==iter_chunk_size):
                    #    raise ValueError('Size of function return value along iteration dimensions must be iter_chunk_size.')
                    y_shape[iter_dims]=iter_shape
                else:
                    y_shape=np.zeros(ndim_xs,dtype=int)
                    y_shape[iter_dims]=iter_shape
                    y_shape[vec_dims]=(1,)*(len(vec_dims)-yp.ndim)+yp.shape
                y=np.empty(y_shape,dtype=yp.dtype)
                ys.append(y)

        # Generate slice for inserting function result into each y.
        if keep_iter_dims:
            # We need to index without losing a dimension. See numpy's rules
            # for basic indexing.
            slc=slice_dims([slice(ind*iter_chunk_size,(ind+1)*iter_chunk_size) for ind in iter_inds],iter_dims)
        else:
            slc=slice_dims(iter_inds,iter_dims)

        # Insert function result into each y.
        for yp,y in zip(yps,ys):
            y[slc]=yp

    if print_progress:
        print('Done')
    return ys

def eval_array_fun_chunked(f,x,axis,chunk_length=None,pool=None,log_level=1):
    """Evaluate function of a numpy array in chunks.
    Args:
        f: the function, which should return an array
        x (array): the array
        axis (int): the axis along which the array is to be broken into chunks
        chunk_length (int): the length of each chunk (need not be a submultiple)
        pool (smpq.Manager): if given, pool.map is used to evaluate in parallel
    Returns: the result of f applied to all the chunks, concatenated along axis
    """
    length=x.shape[axis]
    if chunk_length is None:
        chunk_length=length
    starts=range(0,length,chunk_length)
    logger.log(log_level+1,'Splitting x (%s) into %d chunks along axis %d'%(str(x.shape),len(starts),axis))
    xs=[take(x,slice(start,start+chunk_length),axis) for start in starts]
    if pool is not None:
        logger.log(log_level+1,'Calling pool.map')
        ys=list(pool.map(f,xs))
    else:
        ys=[]
        for num,x in enumerate(xs):
            logger.log(log_level+1,'Chunk %d'%num)
            ys.append(f(x))
    logger.log(log_level+1,'Concatenating ys')
    y=concatenate(ys,axis)
    return y
