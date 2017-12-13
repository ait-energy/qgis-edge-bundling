
""" # ------------------------------------------------------------------------------------------------------------------------------------------------
	# Force-Directed Edge Bundling
	#
	# Performance-optimised script version
	# ------------------------------------------------------------------------------------------------------------------------------------------------
"""

##Edge bundling=group
##input_layer=vector
##cluster_field=field input_layer
##use_clustering_result=boolean True
##initial_step_size=number 100.0
##compatibility=number 0.5
##cycles=number 6
##iterations=number 90
##bundled_edges=output vector

import math
import numpy as np
from qgis.core import *
from qgis.gui import *
import qgis.utils
from PyQt4.QtCore import *
import processing
from processing.tools.vector import VectorWriter
from sklearn.cluster import DBSCAN
from datetime import datetime

def forcecalcx(x, y, d) :
    if abs(x) > eps and abs(y) > eps :
        x *= 1.0 / d
    else :
        x = 0.0
    return x
    
def forcecalcy(x, y, d) :
    if abs(x) > eps and abs(y) > eps :
        y *= 1.0 / d
    else :
        y = 0.0
    return y
        
# ------------------------------------ MISC ------------------------------------ #

class MiscUtils:

    # --- Projects point onto line, needed for compatibility computation --- #
    @staticmethod
    def project_point_on_line(Point, Line):
        L = math.sqrt((Line.vertexAt(1).x() - Line.vertexAt(0).x())**2 + (Line.vertexAt(1).y() - Line.vertexAt(0).y())**2)
        if L**2 < 10**(-6):
            L = 10**(-6)
        r = ((Line.vertexAt(0).y() - Point.y()) * (Line.vertexAt(0).y() - Line.vertexAt(1).y()) - 
               (Line.vertexAt(0).x() - Point.x()) * (Line.vertexAt(1).x() - Line.vertexAt(0).x())) / (L**2)
        return QgsPoint(Line.vertexAt(0).x() + r * (Line.vertexAt(1).x() - Line.vertexAt(0).x()), 
                                  Line.vertexAt(0).y() + r * (Line.vertexAt(1).y() - Line.vertexAt(0).y()))


# ------------------------------------ EDGE-CLUSTER  ------------------------------------ #

class EdgeCluster():
    
    def __init__(self, edges):
        self.S = initial_step_size  # Weighting factor (needs to be cached, because will be decreased in every cycle)
        self.I = iterations  		# Number of iterations per cycle (needs to be cached, because will be decreased in every cycle)
        self.edges = edges			# Edges to bundle in this cluster
        self.edge_lengths = []		# Array to cache edge lenghts
        self.E = len(edges)			# Number of edges
        self.EP = 2   				# Current number of edge points
        self.SP = 0  				# Current number of subdivision points
        self.compatibility_matrix = np.zeros(shape=(self.E,self.E)) # Compatibility matrix
        self.direction_matrix = np.zeros(shape=(self.E,self.E))   	# Encodes direction of edge pairs
        self.N = ( 2 ** cycles ) + 1   								# Maximum number of points per edge
        self.epm_x = np.zeros(shape=(self.E,self.N))				# Bundles edges (x-values)
        self.epm_y = np.zeros(shape=(self.E,self.N))				# Bundles edges (y-values)
        
    # --- Computing the edges compatibility matrix --- #
    def compute_compatibilty_matrix(self):
        
        """ Parameters """
        edges_as_geom = []
        edges_as_vect = []
        for e_idx, edge in enumerate(self.edges) :
            geom = edge.geometry()
            edges_as_geom.append(geom)
            edges_as_vect.append( QgsVector( geom.vertexAt(1).x() - geom.vertexAt(0).x(), geom.vertexAt(1).y() - geom.vertexAt(0).y() ) )
            self.edge_lengths.append( edges_as_vect[e_idx].length() )
            
        """ Compute compatibility: """
	""" Check that length > 0: """
            if edges_as_vect[e_idx].length() == 0:
                print 'Line with length 0 found, please pre-process the data first'
                break
            
	""" Check that number of vertices <= 2: """
            n   = 1
            ver = geom.vertexAt(0)
            points=[]

            while(ver != QgsPoint(0,0)):
                n +=1
                points.append(ver)
                ver=geom.vertexAt(n)

            if n > 2:
                print 'Line has more than 2 vertices, please pre-process the data first'
                break
        """Compatibility is stored in a matrix (rows = edges, columns = edges). Every coordinate in the matrix tells whether the two edges (r,c)/(c,r) are compatible, or not.
        The diagonal is always zero, and the other fields are filled with either -1 (not compatible) or 1 (compatible). The matrix is symmetric. """
        
        progress = 0
        
        for i in range(self.E-1) :
            for j in range(i+1, self.E) :
                
                """ Parameters """
                lavg = ( self.edge_lengths[i] + self.edge_lengths[j] ) / 2.0
                dot = edges_as_vect[i].normalized() * edges_as_vect[j].normalized()
                    
                """ Angle compatibility """
                angle_comp = abs( dot )
                        
                """ Scale compatibility """
                scale_comp = 2.0 / ( lavg / min(self.edge_lengths[i], self.edge_lengths[j]) + max(self.edge_lengths[i], self.edge_lengths[j]) / lavg )
                        
                """ Position compatibility """
                e1_mid = QgsPoint( (edges_as_geom[i].vertexAt(0).x() + edges_as_geom[i].vertexAt(1).x()) / 2.0, (edges_as_geom[i].vertexAt(0).y() + edges_as_geom[i].vertexAt(1).y()) / 2.0 )
                e2_mid = QgsPoint( (edges_as_geom[j].vertexAt(0).x() + edges_as_geom[j].vertexAt(1).x()) / 2.0, (edges_as_geom[j].vertexAt(0).y() + edges_as_geom[j].vertexAt(1).y()) / 2.0 )
                diff = QgsVector( e2_mid.x() - e1_mid.x(), e2_mid.y() - e1_mid.y() )
                pos_comp = lavg / (lavg + diff.length())
                    
                """ Visibility compatibility """
                mid_E1 = edges_as_geom[i].centroid()
                mid_E2 = edges_as_geom[j].centroid()
                dist = mid_E1.distance(mid_E2)
                I0 = MiscUtils.project_point_on_line(edges_as_geom[j].vertexAt(0), edges_as_geom[i])
                I1 = MiscUtils.project_point_on_line(edges_as_geom[j].vertexAt(1), edges_as_geom[i])
                mid_I = QgsGeometry.fromPolyline([I0, I1]).centroid()
                dist_I = I0.distance(I1)
                if dist_I == 0.0 :
                    visibility = 0.0
                else :
                    visibility1 = max(0, 1 - ((2 * mid_E1.distance(mid_I)) / dist_I))
                J0 = MiscUtils.project_point_on_line(edges_as_geom[i].vertexAt(0), edges_as_geom[j])
                J1 = MiscUtils.project_point_on_line(edges_as_geom[i].vertexAt(1), edges_as_geom[j])
                mid_J = QgsGeometry.fromPolyline([J0, J1]).centroid()
                dist_J = J0.distance(J1)
                if dist_J == 0.0 :
                    visibility2 = 0.0
                else :
                    visibility2 = max(0, 1 - ((2 * mid_E2.distance(mid_J)) / dist_J))
                visibility_comp = min(visibility1, visibility2)

                """ Compatibility score """
                comp_score = angle_comp * scale_comp * pos_comp * visibility_comp
                    
                """ Fill values into the matrix (1 = yes, -1 = no) and use matrix symmetry (i/j = j/i) """
                if comp_score >= compatibility :
                    self.compatibility_matrix[i,j] = 1
                    self.compatibility_matrix[j,i] = 1
                else :
                    self.compatibility_matrix[i,j] = -1
                    self.compatibility_matrix[j,i] = -1
                    
                """ Store direction """
                distStart1 = math.sqrt( (edges_as_geom[j].vertexAt(0).x() - edges_as_geom[i].vertexAt(0).x()) * (edges_as_geom[j].vertexAt(0).x() - edges_as_geom[i].vertexAt(0).x()) + (edges_as_geom[j].vertexAt(0).y() - edges_as_geom[i].vertexAt(0).y()) * (edges_as_geom[j].vertexAt(0).y() - edges_as_geom[i].vertexAt(0).y()) )
                distStart2 = math.sqrt( (edges_as_geom[j].vertexAt(1).x() - edges_as_geom[i].vertexAt(0).x()) * (edges_as_geom[j].vertexAt(1).x() - edges_as_geom[i].vertexAt(0).x()) + (edges_as_geom[j].vertexAt(1).y() - edges_as_geom[i].vertexAt(0).y()) * (edges_as_geom[j].vertexAt(1).y() - edges_as_geom[i].vertexAt(0).y()) )
                if distStart1 > distStart2 :
                    self.direction_matrix[i,j] = -1
                    self.direction_matrix[j,i] = -1
                else :
                    self.direction_matrix[i,j] = 1
                    self.direction_matrix[j,i] = 1
    
    # --- Force-directed edge bundling --- #
    def force_directed_eb(self):
        
        """ Create compatibility matrix """
        self.compute_compatibilty_matrix()
        
        """ Initialization """
        for e_idx, edge in enumerate(self.edges) :
            vertices = edge.geometry().asPolyline()
            self.epm_x[e_idx,0] = vertices[0].x()
            self.epm_y[e_idx,0] = vertices[0].y()
            self.epm_x[e_idx,self.N-1] = vertices[1].x()
            self.epm_y[e_idx,self.N-1] = vertices[1].y()
        
        """ --- For all cycles --- """
        for c in range(cycles) :
            
            print 'Cycle {0}'.format(c)
            
            """ New number of subdivision points """
            current_num = self.EP
            currentindeces = []
            for i in range(current_num) :
                idx = int(( float(i) / float(current_num - 1) ) * float(self.N - 1))
                currentindeces.append(idx)
            self.SP += 2 ** c
            self.EP = self.SP + 2
            edgeindeces = []
            newindeces = []
            for i in range(self.EP) :
                idx = int(( float(i) / float(self.EP - 1) ) * float(self.N - 1))
                edgeindeces.append(idx)
                if idx not in currentindeces :
                    newindeces.append(idx)
            pointindeces = edgeindeces[1:self.EP-1]

            """ Calculate position of new points """
            for idx in newindeces :
                i = int( ( float(idx) / float(self.N - 1) ) * float(self.EP - 1) )
                left = i - 1
                leftidx = int(( float(left) / float(self.EP - 1) ) * float(self.N - 1))
                right = i + 1
                rightidx = int(( float(right) / float(self.EP - 1) ) * float(self.N - 1))
                self.epm_x[:,idx] = ( self.epm_x[:,leftidx] + self.epm_x[:,rightidx] ) / 2.0
                self.epm_y[:,idx] = ( self.epm_y[:,leftidx] + self.epm_y[:,rightidx] ) / 2.0
            
            """ Needed for spring forces """
            KP0 = np.zeros(shape=(self.E,1))
            KP0[:,0] = np.asarray(self.edge_lengths)
            KP = K / (KP0 * (self.EP - 1) )

            """ --- For all iterations (number decreased in every cycle) --- """
            for it in range(self.I) :
                
                """ Spring forces """
                middlepoints_x = self.epm_x[:,pointindeces]
                middlepoints_y = self.epm_y[:,pointindeces]
                neighbours_left_x = self.epm_x[:,edgeindeces[0:self.EP-2]]
                neighbours_left_y = self.epm_y[:,edgeindeces[0:self.EP-2]]
                neighbours_right_x = self.epm_x[:,edgeindeces[2:self.EP]]
                neighbours_right_y = self.epm_y[:,edgeindeces[2:self.EP]]
                springforces_x = ( neighbours_left_x - middlepoints_x + neighbours_right_x - middlepoints_x ) * KP
                springforces_y = ( neighbours_left_y - middlepoints_y + neighbours_right_y - middlepoints_y ) * KP
                    
                """ Electrostatic forces: """
                electrostaticforces_x = np.zeros(shape=(self.E,self.SP))
                electrostaticforces_y = np.zeros(shape=(self.E,self.SP))
                """ Loop through all edges """
                for e_idx, edge in enumerate(self.edges) :
                    """ Loop through compatible edges """
                    comp_list = np.where( self.compatibility_matrix[:,e_idx] > 0 )
                    for other_idx in np.nditer(comp_list, ['zerosize_ok']) :
                        otherindeces = pointindeces[:]
                        if self.direction_matrix[e_idx,other_idx] < 0 :
                            otherindeces.reverse()
                        """ Distance between points """
                        subtr_x = self.epm_x[other_idx,otherindeces] - self.epm_x[e_idx,pointindeces]
                        subtr_y = self.epm_y[other_idx,otherindeces] - self.epm_y[e_idx,pointindeces]
                        distance = np.sqrt( np.add( np.multiply( subtr_x, subtr_x ), np.multiply( subtr_y, subtr_y ) ) )
                        flocal_x = map(forcecalcx, subtr_x, subtr_y, distance)
                        flocal_y = map(forcecalcy, subtr_x, subtr_y, distance)
                        """ Sum of forces """
                        electrostaticforces_x[e_idx,:] += flocal_x
                        electrostaticforces_y[e_idx,:] += flocal_y
                        
                """ Compute total forces: """
                force_x = ( springforces_x + electrostaticforces_x ) * self.S
                force_y = ( springforces_y + electrostaticforces_y ) * self.S
                    
                """ Compute new point positions: """
                self.epm_x[:,pointindeces] += force_x
                self.epm_y[:,pointindeces] += force_y

            """ --- Adjustments for next cycle --- """
            self.S = self.S * sdc     # Decrease weighting factor
            self.I = int(round(self.I * idc))       # Decrease iterations

        
        """ --- QGis lines --- """
        for e_idx in range(self.E) :
            """ Create a new polyline out of the line array """
            line = map(lambda p,q : QgsPoint(p,q), self.epm_x[e_idx], self.epm_y[e_idx] )
            """ Create a new line geometry """
            self.edges[e_idx].setGeometry( QgsGeometry.fromPolyline(line) )


# ------------------------------------ SCRIPT START  ------------------------------------ #

# Start
t_start = datetime.now()
print '{0}: Bundling edges (JS)'.format(t_start)
progress.setText('Initialising...')

# Parameter
vlayer=processing.getObject(input_layer)
fields = vlayer.fields()
idc = 0.6666667   # For decreasing iterations
sdc = 0.5  # For decreasing the step-size
K = 0.1
eps = 0.000001

# Create edge list
edges = []
for feature in vlayer.getFeatures() :
    edges.append(feature)

# Create clusters
clusters = []
if use_clustering_result == True :
    # Arrange edges in clusters according to cluster-id
    labels = []
    for edge in edges :
        labels.append(edge[cluster_field])
    for l in range(0,max(labels)+1) :
        clusters.append(list())
    for i,label in enumerate(labels) :
        if label >= 0 : 
            clusters[label].append(edges[i])
        else :
            clusters.append([edges[i]])
    for i,cluster in enumerate(clusters) :
        clusters[i] = EdgeCluster(cluster)
else :
    # If clustering should not be used, create only one big cluster containing all edges
    cluster_field = QgsField('CLUSTER', QVariant.Int)
    clustern_field = QgsField('CLUSTER_N', QVariant.Int)
    fields.append(cluster_field)
    fields.append(clustern_field)
    clusters = [EdgeCluster(edges)]

# Do edge-bundling (separately for all clusters)
for c,cl in enumerate(clusters) :
    if cl.E > 1 :
        cl.force_directed_eb()
    progress.setPercentage(10 + 80 * (c / len(clusters)))

# Plot network
progress.setPercentage(90)
progress.setText('Create output...')
writer = processing.VectorWriter(bundled_edges, None, fields, QGis.WKBLineString, vlayer.crs())
for cl in clusters:
    for e,edge in enumerate(cl.edges) :
        feat = QgsFeature()
        feat.setGeometry( edge.geometry() )
        if use_clustering_result == False :
            attr = edge.attributes()
            attr.append(1)
            attr.append(len(edges))
            feat.setAttributes( attr )
        else :
            feat.setAttributes( edge.attributes() )
        writer.addFeature( feat )
del writer

# End
t_end = datetime.now()
print '{0}: Finished!'.format(t_end)
print 'Run time: {0}'.format(t_end - t_start)
progress.setPercentage(100)
progress.setText('Finished')

# ------------------------------------ SCRIPT END ------------------------------------ #
