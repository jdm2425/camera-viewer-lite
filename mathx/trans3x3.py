import numpy as np

def rotation_x(theta):
    """Right-hand rotation around x by theta radians."""
    theta=np.asarray(theta)
    zeros=np.zeros(theta.shape)
    ones=np.ones(theta.shape)
    cos=np.cos(theta)
    sin=np.sin(theta)
    return [[ones, zeros,zeros],
            [zeros,cos,  -sin],
            [zeros,sin,  cos]]
