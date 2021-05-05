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

from qgis.core import QgsLayerTreeRegistryBridge
from qgis.gui import QgisInterface

from solocator.core.layer import SoLayer, SoGroup
from solocator.core.loading_options import LoadingOptions
from solocator.core.loading_mode import LoadingMode
from solocator.core.data_products import LAYER_GROUP, FACADE_LAYER, force_wms
from solocator.core.utils import dbg_info
from solocator.core.settings import Settings, PG_SERVICE

DEFAULT_CRS = 'EPSG:2056'


class LayerLoader:
    def __init__(self, data: dict, iface: QgisInterface, is_background: bool, alternate_mode: bool = False):

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

        data = self.reformat_data(data, is_background)

        settings = Settings()
        loading_mode: LoadingMode = settings.value('default_layer_loading_mode')
        if alternate_mode:
            loading_mode = loading_mode.alternate_mode()

        if force_wms(data, is_background):
            loading_mode = LoadingMode.WMS

        # if background, insert at bottom of layer tree
        if is_background:
            root = iface.layerTreeView().model().rootGroup()
            pos = len(root.children())
            insertion_point = QgsLayerTreeRegistryBridge.InsertionPoint(root, pos)

        else:
            insertion_point = iface.layerTreeInsertionPoint()

        dbg_info("insertion point: {} {}".format(insertion_point.group.name(), insertion_point.position))

        loading_options = LoadingOptions(
            wms_load_separate=settings.value('wms_load_separate'),
            wms_image_format=settings.value('wms_image_format'),
            loading_mode=loading_mode,
            pg_auth_id=settings.value('pg_auth_id'),
            pg_service=PG_SERVICE
        )

        data.load(insertion_point, loading_options)

    def reformat_data(self, data: dict, is_background: bool):
        """
        Recursive construction of the tree
        :param data:
        :param is_background:
        """
        crs = data.get('crs', DEFAULT_CRS)
        if data['type'] in (LAYER_GROUP, FACADE_LAYER):
            children = [self.reformat_data(child_data, is_background) for child_data in data['sublayers']]
            group_layer = SoLayer(data['display'], is_background, crs, data['wms_datasource'], data.get('postgis_datasource'), data.get('description'), data.get('qml'))
            return SoGroup(data['display'], children, group_layer, data['type'])
        else:
            dbg_info(data.keys())
            return SoLayer(data['display'], is_background,  crs,
                           data['wms_datasource'], data.get('postgis_datasource'),
                           data.get('description'), data.get('qml'))
