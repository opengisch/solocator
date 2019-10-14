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
from tempfile import NamedTemporaryFile

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeWidgetItem

from qgis.core import Qgis, QgsVectorLayer, QgsRasterLayer, QgsProject, QgsDataSourceUri, QgsWkbTypes

from solocator.core.settings import Settings
from solocator.core.data_products import FACADE_LAYER
from solocator.core.utils import info

# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .qgs_layer_tree_insertion_point import InsertionPoint, layerTreeInsertionPoint

HOST = Settings().value('pg_host') or 'geodb.rootso.org'
DB = 'pub'
PORT = '5432'


def postgis_datasource_to_uri(postgis_datasource: dict, pg_auth_id: str, pg_service: str) -> QgsDataSourceUri:
    uri = QgsDataSourceUri()
    if pg_auth_id:
        uri.setConnection(HOST, PORT, DB, None, None, QgsDataSourceUri.SslPrefer, pg_auth_id)
    else:
        uri.setConnection(pg_service, None, None, None, QgsDataSourceUri.SslPrefer)
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


def wms_datasource_to_url(wms_datasource: dict, crs: str, image_format: str) -> str:
    url = "contextualWMSLegend=0&" \
          "crs={crs}&" \
          "dpiMode=7&" \
          "featureCount=10&" \
          "format=image/{image_format}&" \
          "layers={layer}&" \
          "styles&" \
          "url={url}".format(
        crs=crs, image_format=image_format, layer=wms_datasource['name'], url=wms_datasource['service_url']
    )
    return url


class LoadingOptions:
    """
    A class to hold the loading options
    """
    def __init__(self, wms_load_separate: bool, wms_image_format: str,
                 load_as_postgres: bool = False, pg_auth_id: str = None, pg_service: str = None):
        """
        :param wms_load_separate: If True, individual layers will be loaded as separate instead of a single one
        :param wms_image_format: image format
        :param load_as_postgres: If True, tries to load layers as postgres if possible
        :param pg_auth_id: the configuration ID for the authentification
        :param pg_service: the PG service nate
        """
        self.load_as_postgres = load_as_postgres
        self.wms_load_separate = wms_load_separate
        self.pg_auth_id = pg_auth_id
        self.pg_service = pg_service
        self.wms_image_format = wms_image_format

class SoLayer:
    def __init__(self, name: str, crs: str, wms_datasource: dict, postgis_datasource: dict, description: str,
                 qml: str = None):
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
        self.qml = qml

    def __repr__(self):
        return 'SoLayer: {}'.format(self.name)

    def load(self, insertion_point: InsertionPoint, loading_options: LoadingOptions):
        layer = None
        if self.postgis_datasource is not None and loading_options.load_as_postgres:
            uri = postgis_datasource_to_uri(self.postgis_datasource, loading_options.pg_auth_id, loading_options.pg_service)
            if uri:
                layer = QgsVectorLayer(uri.uri(False), self.name, "postgres")
                if self.qml:
                    with NamedTemporaryFile(mode='w', suffix='.qml', delete=False) as fh:
                        fh.write(self.qml)
                        msg, ok = layer.loadNamedStyle(fh.name)
                        fh.close()
                        if not ok:
                            info('SoLocator could not load QML style for layer {}. {}'.format(self.name, msg),
                                 Qgis.Warning)
        if layer is None:
            url = wms_datasource_to_url(self.wms_datasource, self.crs, loading_options.wms_image_format)
            layer = QgsRasterLayer(url, self.name, 'wms')
        QgsProject.instance().addMapLayer(layer, False)
        if not layer.isValid():
            info('Layer {} could not be correctly loaded. Please contact the support.'.format(self.name), Qgis.Warning)
        if insertion_point.position >= 0:
            insertion_point.group.insertLayer(insertion_point.position, layer)
        else:
            insertion_point.group.addLayer(layer)

    def tree_widget_item(self):
        item = QTreeWidgetItem([self.name])
        item.setData(0, Qt.UserRole, deepcopy(self))
        return item


class SoGroup:
    def __init__(self, name, children, layer: SoLayer, _type: str):
        self.name = name
        self.children = children
        self.layer = layer
        self.type = _type

    def __repr__(self):
        return 'SoGroup: {} ( {} )'.format(self.name, ','.join([child.__repr__() for child in self.children]))

    def load(self, insertion_point: InsertionPoint, loading_options: LoadingOptions):
        """
        Loads group in the layer tree
        :param insertion_point: The insertion point in the layer tree (group + position)
        :param load_options: the configuration to load layers
        """
        if not loading_options.load_as_postgres \
                and self.layer.wms_datasource is not None \
                and (not loading_options.wms_load_separate or self.type == FACADE_LAYER):
            self.layer.load(insertion_point, loading_options)
        else:
            if insertion_point.position >= 0:
                group = insertion_point.group.insertGroup(insertion_point.position, self.name)
            else:
                group = insertion_point.group.addGroup(self.name)

            for i, child in enumerate(self.children):
                child.load(InsertionPoint(group, i), loading_options)

    def tree_widget_item(self):
        item = QTreeWidgetItem([self.name])
        item.addChildren([child.tree_widget_item() for child in self.children])
        item.setData(0, Qt.UserRole, deepcopy(self))
        return item
