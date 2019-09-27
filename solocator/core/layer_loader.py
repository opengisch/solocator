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

from copy import deepcopy

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeWidgetItem

from qgis.core import QgsRasterLayer, QgsProject
from qgis.gui import QgisInterface

from solocator.core import solocator_filter
from solocator.gui.load_layer_dialog import LoadLayerDialog


# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .qgs_layer_tree_insertion_point import InsertionPoint, layerTreeInsertionPoint


class SoLayer:
    def __init__(self, name: str, crs: str, wms_datasource: dict, postgis_datasource: dict):
        self.name = name
        self.crs = crs
        self.wms_datasource = wms_datasource
        self.postgis_datasource = postgis_datasource

    def __repr__(self):
        return 'SoLayer: {}'.format(self.name)

    def load(self, insertion_point: InsertionPoint):
        """
        Loads layer in the layer tree
        :param insertion_point: The insertion point in the layer tree (group + position)
        """
        # if type(ds) is list and len(ds) == 1:
        #     ds = ds[0]
        url = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format=image/png&layers={layer}&styles&url={url}".format(
            crs=self.crs, layer=self.wms_datasource['name'], url=self.wms_datasource['service_url']
        )
        layer = QgsRasterLayer(url, self.name, 'wms')
        QgsProject.instance().addMapLayer(layer, False)
        if insertion_point.position >= 0:
            insertion_point.group.insertLayer(insertion_point.position, layer)
        else:
            insertion_point.group.addLayer(layer)

    def tree_widget_item(self):
        item = QTreeWidgetItem([self.name])
        item.setData(0, Qt.UserRole, deepcopy(self))
        return item


class SoGroup:
    def __init__(self, name, children):
        self.name = name
        self.children = children

    def __repr__(self):
        return 'SoGroup: {} ( {} )'.format(self.name, ','.join([child.__repr__() for child in self.children]))

    def load(self, insertion_point: InsertionPoint):
        """
        Loads layer in the layer tree
        :param insertion_point: The insertion point in the layer tree (group + position)
        """
        if insertion_point.position >= 0:
            group = insertion_point.group.insertGroup(insertion_point.position, self.name)
        else:
            group = insertion_point.group.addGroup(self.name)
        for i, child in enumerate(self.children):
            child.load(InsertionPoint(group, i))

    def tree_widget_item(self):
        item = QTreeWidgetItem([self.name])
        item.addChildren([child.tree_widget_item() for child in self.children])
        item.setData(0, Qt.UserRole, deepcopy(self))
        return item


class LayerLoader:
    def __init__(self, data: dict, open_dialog: bool, solocator):
        self.solocator = solocator

        try:
            insertion_point = solocator.iface.layerTreeInsertionPoint()
        except AttributeError:
            # backward compatibility for QGIS < 3.10
            # TODO: remove
            insertion_point = layerTreeInsertionPoint(solocator.iface.layerTreeView())
        solocator.dbg_info("insertion point: {} {}".format(insertion_point.group.name(), insertion_point.position))

        # debug
        for i, v in data.items():
            if i in ('qml', 'contacts'): continue
            if i == 'sublayers':
                for sublayer in data['sublayers']:
                    for j, u in sublayer.items():
                        if j in ('qml', 'contacts'): continue
                        solocator.dbg_info('*** sublayer {}: {}'.format(j, u))
            else:
                solocator.dbg_info('*** {}: {}'.format(i, v))

        data = self.reformat_data(data)

        solocator.dbg_info(data)

        if not open_dialog or LoadLayerDialog(data).exec_():
            data.load(insertion_point)

    def reformat_data(self, data: dict):
        if data['type'] == solocator_filter.LAYER_GROUP:
            children = [self.reformat_data(child_data) for child_data in data['sublayers']]
            return SoGroup(data['display'], children)
        else:
            crs = data.get('crs', solocator_filter.DEFAULT_CRS)
            return SoLayer(data['display'], crs, data['wms_datasource'], data.get('postgis_datasource'))
