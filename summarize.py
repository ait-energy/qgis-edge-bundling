##Edge bundling=group
##input_layer=vector
##cluster_field=field input_layer
##weight_field=field input_layer
##use_weight_field=boolean true
##max_distance=number 0.008
##collapsed_lines=output vector

from qgis.core import *
from qgis.gui import *
import qgis.utils
from PyQt4.QtCore import *
import processing
from processing.tools.vector import VectorWriter
from datetime import datetime 

class Edge(QgsFeature):
    def __init__(self, feature, weight=1):
        super(Edge,self).__init__(feature)
        if use_weight_field: 
            self.weight = float(self.attributes()[weight_index]) #self[weight_field] 
        else:
            self.weight = weight 
        self.agg_weight = self.weight
    
    def increase_weight(self,value=1):
        self.agg_weight += value
    
    def get_weight(self):
        return self.weight 
        
    def get_agg_weight(self):
        return self.agg_weight
        
    
class EdgeCluster():
    def __init__(self,edges):
        self.edges = edges       
        self.index = QgsSpatialIndex()
        for e in self.edges:
            self.index.insertFeature(e)
        self.allfeatures = {edge.id(): edge for (edge) in self.edges}
    
    def get_size(self):
        return len(self.edges) 
    
    def collapse_lines(self):
        ids_to_delete = []
        for edge1 in self.edges:
            geom1 = edge1.geometry()
            # get other edges in the vicinty
            tolerance = min(max_distance,geom1.length()/2)
            ids = self.index.intersects(edge1.geometry().buffer(tolerance,4).boundingBox())
            
            for id in ids:
                edge2 = self.allfeatures[id]            
                if edge1.id()>edge2.id():
                    geom2 = edge2.geometry()
                    d0 = geom1.vertexAt(0).distance(geom2.vertexAt(0))
                    d1 = geom1.vertexAt(1).distance(geom2.vertexAt(1))
                    distance = d0 + d1
                    if d0 <= (tolerance/2) and d1 <= (tolerance/2):
                        edge1.increase_weight(edge2.get_weight())
                        edge2.increase_weight(edge1.get_weight()) 
        return ids_to_delete


t_start = datetime.now()
print '{0}: Collapsing lines'.format(t_start)

layer = processing.getObject(input_layer)
crs = layer.crs()
provider = layer.dataProvider()
fields = provider.fields()
fields.append(QgsField('SEG_ID',QVariant.Int))
fields.append(QgsField('MERGED_N', QVariant.Double))
writer = processing.VectorWriter(collapsed_lines, None, fields, QGis.WKBLineString, crs)
features = list(processing.features(layer))
weight_index = provider.fieldNameIndex(weight_field)

# get all labels from the input features 
labels = []
for feat in features:
    labels.append(int(feat[cluster_field]))
    
# one cluster per label
clusters = []
for l in range(0,max(labels)+1):
    clusters.append(list())

# populate clusters
vl = QgsVectorLayer("LineString", "line_segments", "memory")
pr = vl.dataProvider()
pr.addAttributes(fields)
vl.updateFields()



feature_id = 0 
#all_segments = []
for i,label in enumerate(labels):
    attrs = features[i].attributes()
    polyline = features[i].geometry().asPolyline()
    fet = QgsFeature()
    for j in range(0,len(polyline)-1):
        g = QgsGeometry.fromPolyline([polyline[j],polyline[j+1]])
        fet.setGeometry(g)
        fet.setAttributes(attrs+[j])
        fet.setFeatureId(feature_id)
        feature_id += 1
        edge = Edge(fet)
        #all_segments.append(edge)
        if label >= 0: 
            clusters[label].append(edge)
        else:
            clusters.append(edge)
            
#pr.addFeatures(all_segments)

            
for i,cluster in enumerate(clusters):
    clusters[i] = EdgeCluster(cluster)            
       
# collapse lines 
ids_to_delete = []
for i,cluster in enumerate(clusters):
    print 'Cluster #{0} (size: {1})'.format(i,cluster.get_size())
    ids_to_delete += cluster.collapse_lines()

# create output 
for cluster in clusters:
    for g,edge in enumerate(cluster.edges):
        #if edge.id() not in ids_to_delete:
            fet = QgsFeature()
            fet.setGeometry( edge.geometry() )
            attrs = edge.attributes()
            attrs.append(int(edge.get_agg_weight()))
            fet.setAttributes( attrs )
            writer.addFeature( fet )
del writer                


t_end = datetime.now()
print '{0}: Finished!'.format(t_end)
print 'Run time: {0}'.format(t_end - t_start)