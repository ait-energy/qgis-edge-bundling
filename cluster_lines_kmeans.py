##Edge bundling=group
##input=vector
##metric=string euclidean
##edge_point_clusters=number 2
##kmeans_output=output vector

import numpy as np
import processing 
from processing.tools.vector import VectorWriter
from qgis.core import *
from PyQt4.QtCore import *
from sklearn.cluster import KMeans
from datetime import datetime
from math import sqrt 

t_start = datetime.now()
print '{0}: Clustering using KMeans'.format(t_start)

layer = processing.getObject(input)
provider = layer.dataProvider()
fields = provider.fields()
fields.append(QgsField('CLUSTER', QVariant.Int))
fields.append(QgsField('CLUSTER_N', QVariant.Int))
writer = VectorWriter(kmeans_output, None,fields, provider.geometryType(), layer.crs() )


# Perform clustering 
X = []
for edge in processing.features(layer):
    geom = edge.geometry()
    azimuth = geom.vertexAt(0).azimuth(geom.vertexAt(1))/4
    
    X.append([geom.vertexAt(0).x(),geom.vertexAt(0).y()])
    X.append([geom.vertexAt(1).x(),geom.vertexAt(1).y()])
    

db = KMeans(n_clusters=edge_point_clusters).fit(X)
pt_labels = list(db.labels_)

# labels[0] = cluster of line0 start 
# labels[1] = cluster of line0 end
# labels[2] = cluster of line1 start
# labels[3] = cluster of line1 end
# ...

label_pairs=[]
for ptl in pt_labels:
    try:
        label_pairs[-1]
    except IndexError:
        label_pairs.append([])
    if len(label_pairs[-1]) < 2:
        label_pairs[-1].append(ptl)
    else:
        label_pairs[-1].sort() # to ignore line direction 
        label_pairs.append([ptl])

unique_line_labels = []
labels = []
for pair in label_pairs:
    if pair not in unique_line_labels:
        unique_line_labels.append(pair)
    pair_line_label = unique_line_labels.index(pair)
    labels.append(pair_line_label)

# Determine number of edges per cluster 
cluster_sizes = []
for l in range(0,max(labels)+1):
    cluster_sizes.append(0)
     
for label in labels:
    if label >= 0:
        cluster_sizes[label] = cluster_sizes[label]+1


# Create output 
outFeat = QgsFeature()
for i,inFeat in enumerate(processing.features(layer)):
    inGeom = inFeat.geometry()
    outFeat.setGeometry(inGeom)
    attrs = inFeat.attributes()
    label = int(labels[i])
    attrs.append(label)
    size = 1
    if label >= 0:
        size = int(cluster_sizes[label])
    attrs.append(size)
    outFeat.setAttributes(attrs)
    writer.addFeature(outFeat)

del writer


# Score cluster quality
# size of convex hull of start points or end points per cluster, respectively 
start_points = []
end_points = []
for l in range(0,max(labels)+1):
    start_points.append(QgsMultiPointV2())
    end_points.append(QgsMultiPointV2())

for i,inFeat in enumerate(processing.features(layer)):
    geom = inFeat.geometry()
    label = int(labels[i])
    if label >= 0:
        start_points[label].addGeometry(QgsPointV2(geom.vertexAt(0).x(),geom.vertexAt(0).y()))
        end_points[label].addGeometry(QgsPointV2(geom.vertexAt(1).x(),geom.vertexAt(1).y()))
 
start_areas = [QgsGeometry(pts).convexHull().area() for pts in start_points]
end_areas = [QgsGeometry(pts).convexHull().area() for pts in end_points]
sizes = start_areas  + end_areas
mean = sum(sizes) / len(sizes)

print("Mean area: {0} or approx {1}^2".format(mean, sqrt(mean) ))
print("Max area: {0} or approx {1}^2".format(max(sizes), sqrt(max(sizes)) ))


t_end = datetime.now()
print('{0}: Finished!'.format(t_end))
print('Run time: {0}'.format(t_end - t_start))
