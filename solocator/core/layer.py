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

from qgis.core import Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsDataSourceUri, QgsWkbTypes

from solocator.core.utils import info

# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .qgs_layer_tree_insertion_point import InsertionPoint, layerTreeInsertionPoint

HOST = 'geodb-i.rootso.org'
DB = 'pub'
PORT = '5432'


def postgis_datasource_to_uri(postgis_datasource: dict, pg_auth_id: str) -> QgsDataSourceUri:
    uri = QgsDataSourceUri()
    uri.setConnection(HOST, PORT, DB, None, None, QgsDataSourceUri.SslPrefer, pg_auth_id)
    [schema, table_name] = postgis_datasource['data_set_name'].split('.')
    uri.setDataSource(schema, table_name, postgis_datasource['geometry_field'])
    uri.setKeyColumn(postgis_datasource['primary_key'])
    if postgis_datasource['geometry_type'] == 'POINT':
        wkb_type = QgsWkbTypes.Point
    elif postgis_datasource['geometry_type'] == 'MULITPOINT':
        wkb_type = QgsWkbTypes.MultiPoint
    elif postgis_datasource['geometry_type'] == 'POLYGON':
        wkb_type = QgsWkbTypes.Polygon
    elif postgis_datasource['geometry_type'] == 'MULTIPOLYGON':
        wkb_type = QgsWkbTypes.MultiPolygon
    elif postgis_datasource['geometry_type'] == 'LINESTRING':
        wkb_type = QgsWkbTypes.LineString
    elif postgis_datasource['geometry_type'] == 'MULTILINESTRING':
        wkb_type = QgsWkbTypes.MultiLineString
    else:
        info('SoLocator unterstützt den Geometrietyp {geometry_type} nicht. Bitte kontaktieren Sie den Support.'.format(
            geometry_type=postgis_datasource['geometry_type']), Qgis.Warning
        )
    uri.setWkbType(wkb_type)
    uri.setSrid(str(postgis_datasource.get('srid', 2056)))
    return uri


def wms_datasource_to_url(wms_datasource: dict, crs: str) -> str:
    url = "contextualWMSLegend=0&" \
          "crs={crs}&" \
          "dpiMode=7&" \
          "featureCount=10&" \
          "format=image/png&" \
          "layers={layer}&" \
          "styles&" \
          "url={url}".format(
        crs=crs, layer=wms_datasource['name'], url=wms_datasource['service_url']
    )
    return url


class SoLayer:
    def __init__(self, name: str, crs: str, wms_datasource: dict, postgis_datasource: dict, description: str):
        self.name = name
        self.crs = crs
        self.description = description
        # fix for wms_datasource
        if type(wms_datasource) is list and len(wms_datasource) == 1:
            wms_datasource = wms_datasource[0]
        if type(postgis_datasource) is list and len(postgis_datasource) == 1:
            postgis_datasource = postgis_datasource[0]
        self.wms_datasource = wms_datasource
        self.postgis_datasource = postgis_datasource

    def __repr__(self):
        return 'SoLayer: {}'.format(self.name)

    def load(self, insertion_point: InsertionPoint, load_as_postgres: bool = False, pg_auth_id: str = None):
        """
        Loads layer in the layer tree
        :param insertion_point: The insertion point in the layer tree (group + position)
        :param load_as_postgres: If True, tries to load layers as postgres if possible
        :param pg_auth_id: the configuration ID for the authentification
        """
        layer = None
        if self.postgis_datasource is not None and load_as_postgres:
            uri = postgis_datasource_to_uri(self.postgis_datasource, pg_auth_id)
            if uri:
                layer = QgsVectorLayer(uri.uri(), self.name, "postgres")
        if layer is None:
            url = wms_datasource_to_url(self.wms_datasource, self.crs)
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
    def __init__(self, name, children, layer: SoLayer):
        self.name = name
        self.children = children
        self.layer = layer

    def __repr__(self):
        return 'SoGroup: {} ( {} )'.format(self.name, ','.join([child.__repr__() for child in self.children]))

    def load(self, insertion_point: InsertionPoint, load_as_postgres: bool, pg_auth_id: str):
        """
        Loads group in the layer tree
        :param insertion_point: The insertion point in the layer tree (group + position)
        :param load_as_postgres: If True, tries to load layers as postgres if possible
        :param pg_auth_id: the configuration ID for the authentification
        """
        if not load_as_postgres and self.layer.wms_datasource is not None:
            self.layer.load(insertion_point)
        else:
            if insertion_point.position >= 0:
                group = insertion_point.group.insertGroup(insertion_point.position, self.name)
            else:
                group = insertion_point.group.addGroup(self.name)

            for i, child in enumerate(self.children):
                child.load(InsertionPoint(group, i), load_as_postgres, pg_auth_id)

    def tree_widget_item(self):
        item = QTreeWidgetItem([self.name])
        item.addChildren([child.tree_widget_item() for child in self.children])
        item.setData(0, Qt.UserRole, deepcopy(self))
        return item
