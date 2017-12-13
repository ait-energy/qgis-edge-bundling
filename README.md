# QGIS Edge Bundling

Implementation of force-directed edge bundling for the QGIS Processing toolbox as described in 

https://anitagraser.com/2017/10/08/movement-data-in-gis-8-edge-bundling-for-flow-maps/

and

Graser, A., Schmidt, J., Roth, F., & Brändle, N. (2017 online) Untangling Origin-Destination Flows in Geographic Information Systems. Information Visualization - Special Issue on Visual Movement Analytics. doi:10.1177/1473871617738122. 

## Installation

Copy the files to your Processing scripts folder. By default, it is located in your user home, e.g. <pre> C:\Users\name\\.qgis2\processing\scripts</pre>
 
If you get the error "No module named sklearn.cluster See log for more details", you need to install scikit-learn: 
On Windows, you need to install QGIS using the OSGeo4W installer. In the OSGeo4W, shell run:

<pre>pip install -U scikit-learn</pre>

## Usage

Pre-process your data first! Your data should only contain lines with exactly 2 nodes: an origin node and a destination node. Your data should also only contain lines with a length greater than 0 ("lines" with equal origin and destination node coordinates will cause an error). 

Once your data is sufficiently pre-processed and fulfils all above mentioned requirements, you can either first use one of the clustering algorithms and then bundle the lines, or you can directly bundle the lines (which, on the downside, will take significantly longer). Please double check the input parameters to fit your data (e.g. the "initial step size" in the "edge bundling algorithm" dependent on the coordinate reference system of your data).

Once the lines have been bundled, you can use the summarise tool.

## Examples

Raw origin-destination flows on the left and edge bundling results on the right:

<img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/raw_gulls.png" width="40%"><img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/edge_bundling_gulls.png" width="40%">

<img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/raw_us_migration.png" width="40%"><img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/edge_bundling_us_migration.png" width="40%">

<img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/raw_vienna.png" width="40%"><img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/edge_bundling_vienna.png" width="40%">

<img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/raw_flights.png" width="40%"><img src="https://raw.githubusercontent.com/dts-ait/qgis-edge-bundling/master/images/edge_bundling_flights.png" width="40%">

