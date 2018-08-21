# -*- coding: utf-8 -*-

"""
***************************************************************************
    edgebundlingProviderPlugin.py
    ---------------------
    Date                 : January 2018
    Copyright            : (C) 2018 by Anita Graser
    Email                : anitagraser@gmx.at
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Anita Graser'
__date__ = 'January 2018'
__copyright__ = '(C) 2018, Anita Graser'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsField,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterFeatureSink
                      )

from processing_edgebundling.edgebundlingUtils import EdgeCluster

pluginPath = os.path.dirname(__file__)


class Edgebundling(QgsProcessingAlgorithm):

    INPUT = 'INPUT'
    CLUSTER_FIELD = 'CLUSTER_FIELD'
    USE_CLUSTERING = 'USE_CLUSTERING'
    INITIAL_STEP_SIZE = 'INITIAL_STEP_SIZE'
    COMPATIBILITY = 'COMPATIBILITY'
    CYCLES = 'CYCLES'
    ITERATIONS = 'ITERATIONS'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return type(self)()

    def icon(self):
        return QIcon(os.path.join(pluginPath, "icons", "icon.png"))

    def tr(self, text):
        return QCoreApplication.translate("edgebundling", text)

    def name(self):
        return "edgebundling"

    def displayName(self):
        return self.tr("Force-directed edge bundling")

    def group(self):
        return self.tr("Edge Bundling")

    def groupId(self):
        return "edgebundling"

    def tags(self):
        return self.tr("edgebundling,flows").split(",")

    def shortHelpString(self):
        return self.tr("""
        Implementation of force-directed edge bundling for the QGIS Processing toolbox as described in
        https://anitagraser.com/2017/10/08/movement-data-in-gis-8-edge-bundling-for-flow-maps/
        
        Usage:
        Pre-process your data first! Your data should only contain lines with exactly 2 nodes: an origin node and a destination node. Your data should also only contain lines with a length greater than 0 ("lines" with equal origin and destination node coordinates will cause an error).
        Once your data is sufficiently pre-processed and fulfils all above mentioned requirements, you can either first use one of the clustering algorithms and then bundle the lines, or you can directly bundle the lines (which, on the downside, will take significantly longer). Please double check the input parameters to fit your data (e.g. the "initial step size" in the "edge bundling algorithm" dependent on the coordinate reference system of your data).
        """)

    def helpUrl(self):
        return "https://github.com/dts-ait/qgis-edge-bundling"

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            self.tr("Input layer"),
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterField(
            self.CLUSTER_FIELD,
            self.tr("Cluster field"),
            None,
            self.INPUT))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_CLUSTERING,
            self.tr("Use cluster field"),
            defaultValue=False))
        self.addParameter(QgsProcessingParameterNumber(
            self.INITIAL_STEP_SIZE,
            self.tr("Initial step size"),
            QgsProcessingParameterNumber.Double,
            100))
        self.addParameter(QgsProcessingParameterNumber(
            self.COMPATIBILITY,
            self.tr("Compatibility"),
            QgsProcessingParameterNumber.Double,
            0.6))
        self.addParameter(QgsProcessingParameterNumber(
            self.CYCLES,
            self.tr("Cycles"),
            QgsProcessingParameterNumber.Integer,
            6))
        self.addParameter(QgsProcessingParameterNumber(
            self.ITERATIONS,
            self.tr("Iterations"),
            QgsProcessingParameterNumber.Integer,
            90))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT,
            self.tr("Bundled edges"),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):

        cluster_field = self.parameterAsFields(parameters, self.CLUSTER_FIELD, context)[0]
        use_clustering = self.parameterAsBool(parameters, self.USE_CLUSTERING, context)
        initial_step_size = self.parameterAsDouble(parameters, self.INITIAL_STEP_SIZE, context)
        compatibility = self.parameterAsDouble(parameters, self.COMPATIBILITY, context)
        cycles = self.parameterAsInt(parameters, self.CYCLES, context)
        iterations = self.parameterAsInt(parameters, self.ITERATIONS, context)
        source = self.parameterAsSource(parameters, self.INPUT, context)
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context,
                                               source.fields(), source.wkbType(), source.sourceCrs())

        features = source.getFeatures(QgsFeatureRequest())
        total = 100.0 / source.featureCount() if source.featureCount() else 0

        # Parameter
        vlayer = source
        fields = vlayer.fields()

        # Create edge list
        edges = []
        for current, feat in enumerate(features):
            if feedback.isCanceled():
                break
            edges.append(feat)

        # Create clusters
        clusters = []
        if use_clustering == True:
            # Arrange edges in clusters according to cluster-id
            labels = []
            for edge in edges:
                labels.append(edge[cluster_field])
            feedback.pushDebugInfo(cluster_field)
            for l in range(0, max(labels) + 1):
                clusters.append(list())
            for i, label in enumerate(labels):
                if label >= 0:
                    clusters[label].append(edges[i])
                else:
                    clusters.append([edges[i]])
            for i, cluster in enumerate(clusters):
                clusters[i] = EdgeCluster(cluster, initial_step_size, iterations,
                                    cycles, compatibility)
        else:
            # If clustering should not be used, create only one big cluster containing all edges
            cluster_field = QgsField('CLUSTER', QVariant.Int)
            cluster_n_field = QgsField('CLUSTER_N', QVariant.Int)
            fields.append(cluster_field)
            fields.append(cluster_n_field)
            clusters = [EdgeCluster(edges, initial_step_size, iterations,
                                    cycles, compatibility)]

        # Do edge-bundling (separately for all clusters)
        for c, cl in enumerate(clusters):
            feedback.setProgress(80 * ( 1.0 * c / len(clusters)))
            if feedback.isCanceled(): break
            if cl.E > 1:
                cl.force_directed_eb(feedback)
        feedback.setProgress(90)

        for cl in clusters:
            if feedback.isCanceled(): break
            for e, edge in enumerate(cl.edges):
                feat = QgsFeature()
                feat.setGeometry(edge.geometry())
                if not use_clustering:
                    attr = edge.attributes()
                    attr.append(1)
                    attr.append(len(edges))
                    feat.setAttributes(attr)
                else:
                    feat.setAttributes(edge.attributes())

                sink.addFeature(feat, QgsFeatureSink.FastInsert)

        return {self.OUTPUT: dest_id}
