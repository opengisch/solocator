# -*- coding: utf-8 -*-
"""
/***************************************************************************

 QGIS Swiss Locator Plugin
 Copyright (C) 2018 Denis Rouzaud

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


import json
import os
import re
import sys, traceback

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QLabel, QWidget, QTabWidget
from PyQt5.QtCore import QUrl, QUrlQuery, pyqtSignal, QEventLoop

from qgis.core import Qgis, QgsLocatorFilter, QgsLocatorResult, QgsRectangle, QgsApplication, \
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsGeometry, QgsWkbTypes, QgsPointXY, \
    QgsLocatorContext, QgsFeedback, QgsRasterLayer
from qgis.gui import QgsRubberBand, QgisInterface

from solocator.core.network_access_manager import NetworkAccessManager, RequestsException, RequestsExceptionUserAbort
from solocator.core.settings import Settings
from solocator.gui.config_dialog import ConfigDialog
from solocator.solocator_plugin import DEBUG
#from solocator.utils.html_stripper import strip_tags

import solocator.resources_rc  # NOQA


class FeatureResult:
    def __init__(self, dataproduct_id, id_field_name, id_field_type, feature_id):
        self.dataproduct_id = dataproduct_id
        self.id_field_name = id_field_name
        self.id_field_type = id_field_type
        self.feature_id = feature_id


class NoResult:
    pass


class InvalidBox(Exception):
    pass


class SoLocatorFilter(QgsLocatorFilter):

    HEADERS = {b'User-Agent': b'Mozilla/5.0 QGIS SoLocator Filter'}

    message_emitted = pyqtSignal(str, str, Qgis.MessageLevel, QWidget)

    def __init__(self, iface: QgisInterface = None, crs: str = None):
        """"
        :param filter_type: the type of filter
        :param locale_lang: the language of the locale.
        :param iface: QGIS interface, given when on the main thread (which will display/trigger results), None otherwise
        :param crs: if iface is not given, it shall be provided, see clone()
        """
        super().__init__()
        self.rubber_band = None
        self.feature_rubber_band = None
        self.iface = iface
        self.map_canvas = None
        self.settings = Settings()
        self.transform_ch = None
        self.transform_4326 = None
        self.current_timer = None
        self.crs = None
        self.event_loop = None
        self.result_found = False
        self.nam_fetch_feature = None

        if crs:
            self.crs = crs

        if iface is not None:
            # happens only in main thread
            self.map_canvas = iface.mapCanvas()
            self.map_canvas.destinationCrsChanged.connect(self.create_transforms)

            self.rubber_band = QgsRubberBand(self.map_canvas, QgsWkbTypes.PointGeometry)
            self.rubber_band.setColor(QColor(255, 255, 50, 200))
            self.rubber_band.setIcon(self.rubber_band.ICON_CIRCLE)
            self.rubber_band.setIconSize(15)
            self.rubber_band.setWidth(4)
            self.rubber_band.setBrushStyle(Qt.NoBrush)

            self.feature_rubber_band = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
            self.feature_rubber_band.setColor(QColor(255, 50, 50, 200))
            self.feature_rubber_band.setFillColor(QColor(255, 255, 50, 160))
            self.feature_rubber_band.setBrushStyle(Qt.SolidPattern)
            self.feature_rubber_band.setLineStyle(Qt.SolidLine)
            self.feature_rubber_band.setWidth(4)

            self.create_transforms()

    def name(self):
        return 'SoLocator'

    def clone(self):
        return SoLocatorFilter(crs=self.crs)

    def priority(self):
        return QgsLocatorFilter.Highest

    def displayName(self):
        return 'SoLocator'

    def prefix(self):
        return 'sol'

    def clearPreviousResults(self):
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        if self.feature_rubber_band:
            self.feature_rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        if self.current_timer is not None:
            self.current_timer.stop()
            self.current_timer.deleteLater()
            self.current_timer = None

    def hasConfigWidget(self):
        return True

    def openConfigWidget(self, parent=None):
        dlg = ConfigDialog(parent)
        wid = dlg.findChild(QTabWidget, "tabWidget", Qt.FindDirectChildrenOnly)
        tab = wid.findChild(QWidget, self.type.value)
        wid.setCurrentWidget(tab)
        dlg.exec_()

    def create_transforms(self):
        # this should happen in the main thread
        src_crs_ch = QgsCoordinateReferenceSystem('EPSG:2056')
        assert src_crs_ch.isValid()
        dst_crs = self.map_canvas.mapSettings().destinationCrs()
        self.transform_ch = QgsCoordinateTransform(src_crs_ch, dst_crs, QgsProject.instance())

        src_crs_4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        self.transform_4326 = QgsCoordinateTransform(src_crs_4326, dst_crs, QgsProject.instance())

    @staticmethod
    def box2geometry(box: str) -> QgsRectangle:
        """
        Creates a rectangle from a Box definition as string
        :param box: the box as a string
        :return: the rectangle
        """
        coords = re.findall(r'\b(\d+(?:\.\d+)?)\b', box)
        if len(coords) != 4:
            raise InvalidBox('Could not parse: {}'.format(box))
        return QgsRectangle(float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3]))

    @staticmethod
    def url_with_param(url, params) -> str:
        url = QUrl(url)
        q = QUrlQuery(url)
        for key, value in params.items():
            q.addQueryItem(key, value)
        url.setQuery(q)
        return url.url()

    def fetchResults(self, search: str, context: QgsLocatorContext, feedback: QgsFeedback):
        try:
            self.dbg_info("start solocator search...")

            if len(search) < 2:
                return

            if len(search) < 4 and self.type is FilterType.Feature:
                return

            self.result_found = False

            # see https://geo-t.so.ch/api/search/v2/api/
            url = 'https://geo-t.so.ch/api/search/v2'
            params = {
                'searchtext': str(search),
                'filter': self.settings.enabled_categories(),
                'limit': str(self.settings.value('limit'))

            }

            nam = NetworkAccessManager()
            feedback.canceled.connect(nam.abort)
            url = self.url_with_param(url, params)
            self.dbg_info(url)
            try:
                (response, content) = nam.request(url, headers=self.HEADERS, blocking=True)
                self.handle_response(response)
            except RequestsExceptionUserAbort:
                pass
            except RequestsException as err:
                self.info(err)

            if not self.result_found:
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = self.tr('No result found.')
                result.userData = NoResult
                self.resultFetched.emit(result)

        except Exception as e:
            self.info(e, Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def handle_response(self, response):
        try:
            if response.status_code != 200:
                if not isinstance(response.exception, RequestsExceptionUserAbort):
                    self.info("Error in main response with status code: {} from {}"
                              .format(response.status_code, response.url))
                return

            data = json.loads(response.content.decode('utf-8'))
            # self.dbg_info(data)

            for res in data['results']:
                self.dbg_info(res)

                if 'feature' in res.keys():
                    f = res['feature']
                    self.dbg_info("feature: {}".format(f))

                    result = QgsLocatorResult()
                    result.filter = self
                    result.displayString = f['display']
                    result.group = 'Features'
                    result.userData = FeatureResult(
                        dataproduct_id=f['dataproduct_id'],
                        id_field_name=f['id_field_name'],
                        id_field_type=f['id_field_type'],
                        feature_id=f['feature_id']
                    )
                    result.icon = QIcon(":/plugins/solocator/icons/solocator.png")
                    self.result_found = True
                    self.resultFetched.emit(result)

                elif 'dataproduct' in res.keys():
                    self.dbg_info("dataproduct: {}".format(res['dataproduct']))

                continue








                # available keys: ﻿['origin', 'lang', 'layer', 'staging', 'title', 'topics', 'detail', 'label', 'id']
                for key, val in res['attrs'].items():
                    self.dbg_info('{}: {}'.format(key, val))
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = res['attrs']['title']
                result.description = res['attrs']['layer']
                result.userData = WMSLayerResult(layer=loc['attrs']['layer'], title=loc['attrs']['title'])
                result.icon = QgsApplication.getThemeIcon("/mActionAddWmsLayer.svg")
                self.result_found = True
                self.resultFetched.emit(result)


                for key, val in loc['attrs'].items():
                    self.dbg_info('{}: {}'.format(key, val))
                result = QgsLocatorResult()
                result.filter = self
                layer = loc['attrs']['layer']
                point = QgsPointXY(loc['attrs']['lon'], loc['attrs']['lat'])
                if layer in self.searchable_layers:
                    layer_display = self.searchable_layers[layer]
                else:
                    self.info(self.tr('Layer {} is not in the list of searchable layers.'
                                      ' Please report issue.'.format(layer)), Qgis.Warning)
                    layer_display = layer
                result.group = layer_display
                result.displayString = loc['attrs']['detail']
                result.userData = FeatureResult(point=point,
                                                layer=layer,
                                                feature_id=loc['attrs']['feature_id'])
                result.icon = QIcon(":/plugins/solocator/icons/solocator.png")
                self.result_found = True
                self.resultFetched.emit(result)

                # locations
                for key, val in loc['attrs'].items():
                    self.dbg_info('{}: {}'.format(key, val))
                group_name, group_layer = self.group_info(loc['attrs']['origin'])
                if 'layerBodId' in loc['attrs']:
                    self.dbg_info("layer: {}".format(loc['attrs']['layerBodId']))
                if 'featureId' in loc['attrs']:
                    self.dbg_info("feature: {}".format(loc['attrs']['featureId']))

                result = QgsLocatorResult()
                result.filter = self
                result.displayString = strip_tags(loc['attrs']['label'])
                # result.description = loc['attrs']['detail']
                # if 'featureId' in loc['attrs']:
                #     result.description = loc['attrs']['featureId']
                result.group = group_name
                result.userData = LocationResult(point=QgsPointXY(loc['attrs']['y'], loc['attrs']['x']),
                                                 bbox=self.box2geometry(loc['attrs']['geom_st_box2d']),
                                                 layer=group_layer,
                                                 feature_id=loc['attrs']['featureId'] if 'featureId' in loc['attrs']
                                                 else None,
                                                 html_label=loc['attrs']['label'])
                result.icon = QIcon(":/plugins/solocator/icons/solocator.png")
                self.result_found = True
                self.resultFetched.emit(result)

        except Exception as e:
            self.info(str(e), Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def triggerResult(self, result: QgsLocatorResult):
        # this should be run in the main thread, i.e. mapCanvas should not be None
        
        # remove any previous result
        self.clearPreviousResults()

        if type(result.userData) == NoResult:
            pass

        elif type(result.userData) == FeatureResult:
            self.fetch_feature(result.userData)

        return

        # WMS
        url_with_params = 'contextualWMSLegend=0' \
                          '&crs=EPSG:{crs}' \
                          '&dpiMode=7' \
                          '&featureCount=10' \
                          '&format=image/png' \
                          '&layers={layer}' \
                          '&styles=' \
                          '&url=http://wms.geo.admin.ch/?VERSION%3D2.0.0'\
            .format(crs=self.crs, layer=result.userData.layer)
        wms_layer = QgsRasterLayer(url_with_params, result.displayString, 'wms')
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        if not wms_layer.isValid():
            msg = self.tr('Cannot load WMS layer: {} ({})'.format(result.userData.title, result.userData.layer))
            level = Qgis.Warning
            label.setText('<a href="https://map.geo.admin.ch/'
                          '?lang=fr&bgLayer=ch.swisstopo.pixelkarte-farbe&layers={}">'
                          'Open layer in map.geo.admin.ch</a>'.format(result.userData.layer))
            self.info(msg, level)
        else:
            msg = self.tr('WMS layer added to the map: {} ({})'.format(result.userData.title, result.userData.layer))
            level = Qgis.Info
            label.setText('<a href="https://map.geo.admin.ch/'
                          '?lang=fr&bgLayer=ch.swisstopo.pixelkarte-farbe&layers={}">'
                          'Open layer in map.geo.admin.ch</a>'.format(result.userData.layer))

            QgsProject.instance().addMapLayer(wms_layer)

        self.message_emitted.emit(self.displayName(), msg, level, label)
                
    def highlight(self, point, bbox=None):
        if bbox is None:
            bbox = point
        self.rubber_band.reset(QgsWkbTypes.PointGeometry)
        self.rubber_band.addGeometry(point, None)
        rect = bbox.boundingBox()
        rect.scale(1.1)
        self.map_canvas.setExtent(rect)
        self.map_canvas.refresh()

    def fetch_feature(self, feature: FeatureResult):
        # see https://geo-t.so.ch/api/data/v1/api/
        url = 'https://geo-t.so.ch/api/data/v1/{dataset}/{id}'.format(
            dataset=feature.dataproduct_id, id=feature.feature_id
        )
        self.nam_fetch_feature = NetworkAccessManager()
        self.dbg_info(url)
        self.nam_fetch_feature.finished.connect(self.parse_feature_response)
        self.nam_fetch_feature.request(url, headers=self.HEADERS, blocking=False)

    def parse_feature_response(self, response):
        if response.status_code != 200:
            if not isinstance(response.exception, RequestsExceptionUserAbort):
                self.info("Error in feature response with status code: {} from {}"
                          .format(response.status_code, response.url))
            return

        data = json.loads(response.content.decode('utf-8'))
        self.dbg_info(data.keys())
        self.dbg_info(data['properties'])
        self.dbg_info(data['geometry'])
        self.dbg_info(data['crs'])
        self.dbg_info(data['type'])

        geometry_type = data['geometry']['type']

        if geometry_type == 'Point':
            geometry = QgsGeometry.fromPointXY(QgsPointXY(data['geometry']['coordinates'][0],
                                                          data['geometry']['coordinates'][1]))
            geometry.transform(self.transform_ch)
        elif geometry_type == 'Polygon':
            rings = data['geometry']['coordinates']
            for r in range(0, len(rings)):
                for p in range(0, len(rings[r])):
                    rings[r][p] = QgsPointXY(rings[r][p][0], rings[r][p][1])
            geometry = QgsGeometry.fromPolygonXY(rings)
            geometry.transform(self.transform_ch)
            geometry.transform(self.transform_ch)

        else:
            self.info('SoLocator does not handle {} yet. Please contact support.'.format(geometry_type))

        if 'feature' not in data or 'geometry' not in data['feature']:
            return

        if 'rings' in data['feature']['geometry']:
            rings = data['feature']['geometry']['rings']
            self.dbg_info(rings)
            for r in range(0, len(rings)):
                for p in range(0, len(rings[r])):
                    rings[r][p] = QgsPointXY(rings[r][p][0], rings[r][p][1])
            geometry = QgsGeometry.fromPolygonXY(rings)
            geometry.transform(self.transform_ch)

            self.feature_rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.feature_rubber_band.addGeometry(geometry, None)

    def info(self, msg="", level=Qgis.Info, emit_message: bool = False):
        self.logMessage(str(msg), level)
        if emit_message:
            self.message_emitted.emit(msg, level)

    def dbg_info(self, msg=""):
        if DEBUG:
            self.info(msg)

    @staticmethod
    def break_camelcase(identifier):
        matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
        return ' '.join([m.group(0) for m in matches])
