# -*- coding: utf-8 -*-
"""
/***************************************************************************

 QGIS Solothurn Locator Plugin
 Copyright (C) 2019 Denis Rouzaud

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.core import QgsRasterLayer, QgsProject
from qgis.gui import QgisInterface

from solocator.core import solocator_filter
from solocator.gui.load_layer_dialog import LoadLayerDialog


# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .layer_tree import InsertionPoint, layerTreeInsertionPoint


class LayerLoader:
    def __init__(self, data: dict, open_dialog: bool, solocator):
        self.solocator = solocator

        try:
            insertion_point = self.iface.layerTreeInsertionPoint()
        except AttributeError:
            # backward compatibility for QGIS < 3.10
            # TODO: remove
            insertion_point = layerTreeInsertionPoint(solocator.iface.layerTreeView())

        solocator.dbg_info("insertion point: {} {}".format(insertion_point.parent.name(), insertion_point.position))
        if open_dialog:
            LoadLayerDialog(data, insertion_point).exec_()
        else:
            self.load_layer(data, insertion_point)

    def load_layer(self, data: dict, insertion_point: InsertionPoint):
        """
        Recursive method to load layers / groups
        """
        self.solocator.dbg_info("load_layer call in {}"
                      " at position {}".format(insertion_point.parent.name(), insertion_point.position))
        if type(data) is list:
            for d in data:
                self.load_layer(d, insertion_point)
        else:
            # self.solocator.dbg_info('*** load: {}'.format(data.keys()))
            if data['type'] == solocator_filter.LAYER_GROUP:
                if insertion_point.position >= 0:
                    group = insertion_point.parent.insertGroup(insertion_point.position, data['display'])
                else:
                    group = insertion_point.parent.addGroup(data['display'])

                self.load_layer(data['sublayers'], InsertionPoint(group, -1))
            else:
                self.solocator.dbg_info('*** load: {}'.format(data['wms_datasource']))
                ds = data['wms_datasource']
                if type(ds) is list and len(ds) == 1:
                    ds = ds[0]
                url = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format=image/png&layers={layer}&styles&url={url}".format(
                    crs=data.get('crs', solocator_filter.DEFAULT_CRS), layer=ds['name'], url=ds['service_url']
                )
                layer = QgsRasterLayer(url, data['display'], 'wms')
                QgsProject.instance().addMapLayer(layer, False)
                self.solocator.dbg_info("inserting layer in {}"
                              " at position {}".format(insertion_point.parent.name(), insertion_point.position))
                if insertion_point.position >= 0:
                    insertion_point.parent.insertLayer(insertion_point.position, layer)
                else:
                    insertion_point.parent.addLayer(layer)

                if 'postgis_datasource' in data:
                    self.solocator.dbg_info(data['postgis_datasource'])