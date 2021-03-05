from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsProcessing,
                       QgsSpatialIndex,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterBoolean,
                       QgsVectorLayer
                       )
from qgis import processing
import qgis.utils

from datetime import datetime
t_start = datetime.now()
print ('{0}: Summarize Bundled Edges'.format(t_start))



class SummarizeBundledEdges(QgsProcessingAlgorithm):
    """
    This is a clustering algorithm that the lineStrings in the 
    input layer and assign them to clustr number.
    """
    INPUT='INPUT'
    CLUSTER_FIELD='CLUSTER_FIELD'
    WEIGHT_FIELD='WEIGHT_FIELD'
    USE_WEIGHT_FIELD='USE_WEIGHT_FIELD'
    MAX_DISTANCE='MAX_DISTANCE'
    COLLAPSED_LINES = 'COLLAPSED_LINES' # output
    
    # This will allow the script to be added to the Processing Toolbox
    def __init__(self):
        super().__init__()

# createInstance has to be added, or the algorithm will crash!
    def createInstance(self):
        return type(self)()
        
    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        This translated the name of the file, so let's name the file: summarize
        """
        return QCoreApplication.translate('summarize', string)
        
    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'summarize'
        
    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Summarize the Bundled Edges')
        
    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('Summarize Bundles')
        
    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs
        to.
        """
        return 'summarize'
    
    def shortHelpString(self):
        """
        Returns a localised short help string for the algorithm.
        """
        return self.tr("""
        In this script, the bundled edges will be summarized to provide better visual presentation.
        "ALG_DESC": "Summarize edge bundling results by aggregating the local strength of bundled eges. 
        "ALG_CREATOR": "Anita Graser", 
        "weight_field": "Field with flow weights ", 
        "collapsed_lines": "Line layer with added bundle strength fields", 
        "cluster_field": "Field with cluster IDs", 
        "ALG_VERSION": "1.0", 
        "input_layer": "Edge bundling output lines", 
        "max_distance": "Maximum distance between two lines to still be considered part of the same bundle", 
        "use_weight_field": "Activate if weight field should be used. Otherwise a weight of one will be asumed. ", 
        "ALG_HELP_CREATOR": "Anita Graser"
        """)

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT',
                self.tr('input layer'),
                types=[QgsProcessing.TypeVectorLine]
            )
        )
        # This block will let the user to define the field containing te clusters number
        self.addParameter(QgsProcessingParameterField(
            self.CLUSTER_FIELD,
            self.tr("Cluster field"),
            None,
            self.INPUT))
            
        # This block will let the user to define Field with flow weights
        self.addParameter(QgsProcessingParameterField(
            self.WEIGHT_FIELD,
            self.tr("weight field"),
            None,
            self.INPUT))
        # Boolean input for the use_weight_field
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_WEIGHT_FIELD,
            self.tr("Use weight field"),
            defaultValue=False))
        # Maximum distance between two lines to still be considered part of the same bundle  
        self.addParameter(QgsProcessingParameterNumber(
            self.MAX_DISTANCE,
            self.tr("max distance"),
            QgsProcessingParameterNumber.Double,
            0.6))
        
        # Define the output a feature sink for the result  
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.COLLAPSED_LINES,
            self.tr("collapsed lines"),
            QgsProcessing.TypeVectorLine)
        )
        
    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place. DO SOMETHING!
        """
        # First, introduce the source layer .. 
        # This layer is defined as a QgsProcessingParameterFeatureSource parameter,
        #  so it is retrieved by calling self.parameterAsSource.
        source = self.parameterAsSource(parameters, self.INPUT, context)
        
        cluster_field=self.parameterAsFields(parameters, self.CLUSTER_FIELD, context)[0]
        
        weight_field=self.parameterAsFields(parameters, self.WEIGHT_FIELD, context)[0]
        
        use_weight_field=self.parameterAsBool(parameters, self.USE_WEIGHT_FIELD, context) 
        
        max_distance=self.parameterAsDouble(parameters, self.MAX_DISTANCE, context)
        
        # Parameter Definition: get the source layer/ get the fields of the source layer
        layer = source
        fields = layer.fields()
        
        # Get the features in the source layer / the fields in those features (as above)
        # Define and append two new fields: seg_id & merged_n
        # seg_id: 
        # merged_n:        
        
        features = list(source.getFeatures(QgsFeatureRequest()))
        seg_id=QgsField('SEG_ID', QVariant.Int)
        merged_n=QgsField('MERGED_N', QVariant.Double)
        fields.append(seg_id)
        fields.append(merged_n)
        
        # Introduce the sink that is filled with the output features:
        (sink, dest_id) = self.parameterAsSink(parameters, self.COLLAPSED_LINES, context,
                                               fields, source.wkbType(), source.sourceCrs())
                                               
        
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
        weight_index = pr.fieldNameIndex(weight_field)
        
        #=================================================================================================
        # Class: Edge is a child class of the Parent Class QgsFeatures
        # This Child (Sub-) class is craeted to handle the source layer, 
        # i.e. inherit the typicl attributes of the source QgsFeature ,,
        # then define new feature: weight  agg_weight,,  then define method on increase_weight ,, 
        # and finally get_agg_weight
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
        #======================================================================================================
        feature_id = 0 
        all_segments = []
        for i,label in enumerate(labels):
            attrs = features[i].attributes()
            polyline = features[i].geometry().asPolyline()
            fet = QgsFeature()
            for j in range(0,len(polyline)-1):
                g = QgsGeometry.fromPolylineXY([polyline[j],polyline[j+1]])
                fet.setGeometry(g)
                fet.setAttributes(attrs+[j])
                fet.setId(feature_id)
                feature_id += 1
                edge = Edge(fet)
                all_segments.append(edge)
                if label >= 0: 
                    clusters[label].append(edge)
                else:
                    clusters.append(edge)
        #=======================================================================================================
        # Class: EdgeCluster is a parent (New) class 
        class EdgeCluster():
            def __init__(self,edges):
                self.edges = edges # construct class state/name: edges       
                self.index = QgsSpatialIndex() # create an empty object (index) but its instances customized to a specific initial state that inherts from QgsFeatureSink
                for e in self.edges: # Then, via looping through this customized filled object, we fill our newly created class with the respective QgsFeatureSink features
                    self.index.insertFeature(e)
                self.allfeatures = {edge.id(): edge for (edge) in self.edges} # Collect the final class features
            
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
                            ids_to_delete.append(edge2.id())    # Bishoy: I added this line to make sure redundent edges are removed.. please advise
                return ids_to_delete
        
        #pr.addFeatures(all_segments)
        for i,cluster in enumerate(clusters):
            clusters[i] = EdgeCluster(cluster)
            
        # collapse lines 
        ids_to_delete = []
        for i,cluster in enumerate(clusters):
            print ('Cluster #{0} (size: {1})'.format(i,cluster.get_size()))
            ids_to_delete += cluster.collapse_lines()
            
        # create output 
        for cluster in clusters:
            for g,edge in enumerate(cluster.edges):
                if edge.id() not in ids_to_delete:
                    fet = QgsFeature()
                    fet.setGeometry(edge.geometry())
                    attrs = edge.attributes()
                    attrs.append(int(edge.get_agg_weight()))
                    fet.setAttributes(attrs)
                    sink.addFeature(fet, QgsFeatureSink.FastInsert)
            
        return {self.COLLAPSED_LINES: dest_id}
            
t_end = datetime.now()


print ('{0}: Finished!'.format(t_end))
print ('Run time: {0}'.format(t_end - t_start))
