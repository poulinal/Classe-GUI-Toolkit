#AP 2026
from matplotlib.collections import QuadMesh
import numpy as np

# Extract data from existing QuadMesh
def extract_quadmesh_data(quadmesh : QuadMesh):
    """Get X, Y, Z arrays from QuadMesh object"""
    # Get the array data
    array = quadmesh.get_array()
    coords = quadmesh.get_coordinates()
    
    # Coordinates define cell corners, data is cell centers
    M, N = coords.shape[:2]
    Z = array.reshape(M-1, N-1)  # Data is one smaller in each dimension
    
    X = coords[:, :, 0]
    Y = coords[:, :, 1]
    return X, Y, Z
