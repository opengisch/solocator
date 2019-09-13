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
from PyQt5.QtWidgets import QWidget, QTabWidget
from PyQt5.QtCore import QUrl, QUrlQuery, pyqtSignal

from qgis.core import Qgis, QgsLocatorFilter, QgsLocatorResult, QgsRectangle, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsProject, QgsGeometry, QgsWkbTypes, QgsPointXY, QgsLocatorContext, QgsFeedback
from qgis.gui import QgsRubberBand, QgisInterface

from solocator.core.network_access_manager import NetworkAccessManager, RequestsException, RequestsExceptionUserAbort
from solocator.core.settings import Settings
from solocator.gui.config_dialog import ConfigDialog
from solocator.solocator_plugin import DEBUG

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

    def __init__(self, iface: QgisInterface = None):
        """"
        :param iface: QGIS interface, given when on the main thread (which will display/trigger results), None otherwise
        :param crs: if iface is not given, it shall be provided, see clone()
        """
        super().__init__()

        self.iface = iface
        self.settings = Settings()

        #  following properties will only be used in main thread
        self.rubber_band = None
        self.map_canvas = None
        self.transform_ch = None
        self.current_timer = None
        self.result_found = False
        self.nam_fetch_feature = None

        if iface is not None:
            # happens only in main thread
            self.map_canvas = iface.mapCanvas()
            self.map_canvas.destinationCrsChanged.connect(self.create_transforms)

            self.rubber_band = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
            self.rubber_band.setColor(QColor(255, 50, 50, 200))
            self.rubber_band.setFillColor(QColor(255, 255, 50, 160))
            self.rubber_band.setBrushStyle(Qt.SolidPattern)
            self.rubber_band.setLineStyle(Qt.SolidLine)
            self.rubber_band.setIcon(self.rubber_band.ICON_CIRCLE)
            self.rubber_band.setIconSize(15)
            self.rubber_band.setWidth(4)
            self.rubber_band.setBrushStyle(Qt.NoBrush)

            self.create_transforms()

    def name(self):
        return 'SoLocator'

    def clone(self):
        return SoLocatorFilter()

    def priority(self):
        return QgsLocatorFilter.Highest

    def displayName(self):
        return 'SoLocator'

    def prefix(self):
        return 'sol'

    def clearPreviousResults(self):
        if self.rubber_band:
            self.rubber_band.reset(QgsWkbTypes.PointGeometry)

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

            if len(search) < 3:
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




        except Exception as e:
            self.info(str(e), Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def triggerResult(self, result: QgsLocatorResult):
        # this is run in the main thread, i.e. map_canvas is not None
        
        self.clearPreviousResults()

        if type(result.userData) == NoResult:
            pass

        elif type(result.userData) == FeatureResult:
            self.fetch_feature(result.userData)

    def highlight(self, geometry: QgsGeometry):
        self.clearPreviousResults()

        if geometry is None:
            return

        self.rubber_band.reset(geometry.type())
        self.rubber_band.addGeometry(geometry, None)

        rect = geometry.boundingBox()
        rect.scale(1.1)
        self.map_canvas.setExtent(rect)
        self.map_canvas.refresh()

        self.current_timer = QTimer()
        self.current_timer.timeout.connect(self.clearPreviousResults)
        self.current_timer.setSingleShot(True)
        self.current_timer.start(5000)

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

        assert data['crs']['properties']['name'] == 'urn:ogc:def:crs:EPSG::2056'

        geometry_type = data['geometry']['type']
        geometry = QgsGeometry()

        if geometry_type == 'Point':
            geometry = QgsGeometry.fromPointXY(QgsPointXY(data['geometry']['coordinates'][0],
                                                          data['geometry']['coordinates'][1]))
        elif geometry_type == 'Polygon':
            rings = data['geometry']['coordinates']
            for r in range(0, len(rings)):
                for p in range(0, len(rings[r])):
                    rings[r][p] = QgsPointXY(rings[r][p][0], rings[r][p][1])
            geometry = QgsGeometry.fromPolygonXY(rings)
        else:
            self.info('SoLocator does not handle {} yet. Please contact support.'.format(geometry_type))

        geometry.transform(self.transform_ch)
        self.highlight(geometry)

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
