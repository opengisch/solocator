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


from qgis.gui import QgisInterface

from solocator.core.layer import SoLayer, SoGroup, LoadingOptions
from solocator.core.data_products import LAYER_GROUP, FACADE_LAYER
from solocator.core.utils import dbg_info
from solocator.core.settings import Settings
from solocator.gui.layer_loader_dialog import LayerLoaderDialog

DEFAULT_CRS = 'EPSG:2056'


# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .qgs_layer_tree_insertion_point import InsertionPoint, layerTreeInsertionPoint


class LayerLoader:
    def __init__(self, data: dict, open_dialog: bool, iface: QgisInterface):

        try:
            insertion_point = iface.layerTreeInsertionPoint()
        except AttributeError:
            # backward compatibility for QGIS < 3.10
            # TODO: remove
            insertion_point = layerTreeInsertionPoint(iface.layerTreeView())
        dbg_info("insertion point: {} {}".format(insertion_point.group.name(), insertion_point.position))

        # debug
        for i, v in data.items():
            if i in ('qml', 'contacts'): continue
            if i == 'sublayers':
                for sublayer in data['sublayers']:
                    for j, u in sublayer.items():
                        if j in ('qml', 'contacts'): continue
                        dbg_info('*** sublayer {}: {}'.format(j, u))
            else:
                dbg_info('*** {}: {}'.format(i, v))

        data = self.reformat_data(data)

        if open_dialog:
            dlg = LayerLoaderDialog(data)
            if dlg.exec_():
                data = dlg.first_selected_item()
                loading_options = dlg.loading_options()
            else:
                data = None
        else:
            settings = Settings()
            loading_options = LoadingOptions(settings.value('wms_load_separate'), settings.value('wms_image_format'))

        if data:
            data.load(insertion_point, loading_options)

    def reformat_data(self, data: dict):
        """
        Recursive construction of the tree
        :param data:
        """
        crs = data.get('crs', DEFAULT_CRS)
        if data['type'] in (LAYER_GROUP, FACADE_LAYER):
            children = [self.reformat_data(child_data) for child_data in data['sublayers']]
            group_layer = SoLayer(data['display'], crs, data['wms_datasource'], data.get('postgis_datasource'), data.get('description'), data.get('qml'))
            return SoGroup(data['display'], children, group_layer)
        else:
            return SoLayer(data['display'], crs,
                           data['wms_datasource'], data.get('postgis_datasource'),
                           data.get('description'), data.get('qml'))
