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
import sys
import traceback

from PyQt5.QtCore import Qt, QTimer, QUrl, QUrlQuery, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QWidget, QApplication

from qgis.core import Qgis, QgsLocatorFilter, QgsLocatorResult, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform, QgsProject, QgsGeometry, QgsWkbTypes, QgsPointXY, QgsLocatorContext, QgsFeedback, \
    QgsRasterLayer
from qgis.gui import QgsRubberBand, QgisInterface, QgsMapCanvas, QgsFilterLineEdit

from solocator.core.network_access_manager import NetworkAccessManager, RequestsException, RequestsExceptionUserAbort
from solocator.core.settings import Settings
from solocator.gui.config_dialog import ConfigDialog
from solocator.solocator_plugin import DEBUG

DEFAULT_CRS = 'EPSG:2056'

# Compatibility for QGIS < 3.10
# TODO: remove
try:
    from qgis.gui.QgsLayerTreeRegistryBridge import InsertionPoint
except ModuleNotFoundError:
    from .layertree import InsertionPoint, layerTreeInsertionPoint

import solocator.resources_rc  # NOQA


LAYER_GROUP = 'layergroup'

DATAPRODUCT_TYPE_TRANSLATION = {
    'datasetview': 'Layer',
    'facadelayer': 'Fassadenlayer',
    'background': 'Hintergrundlayer'
}


class FeatureResult:
    def __init__(self, dataproduct_id, id_field_name, id_field_type, feature_id):
        self.dataproduct_id = dataproduct_id
        self.id_field_name = id_field_name
        self.id_field_type = id_field_type
        self.feature_id = feature_id

    def __repr__(self):
        return 'SoLocator Feature: {}/{}'.format(self.dataproduct_id, self.feature_id)


class DataProductResult:
    def __init__(self, type, dataproduct_id, display, dset_info, sublayers):
        self.type = type
        self.dataproduct_id = dataproduct_id
        self.display = display
        self.dset_info = dset_info
        self.sublayers = sublayers

    def __repr__(self):
        return 'SoLocator Data Product: {} {} ()'.format(self.type, self.dataproduct_id, self.dset_info, self.sublayers)


class FilterResult:
    """
    A result holder for sub-filtering
    """
    def __init__(self, filter_word, search):
        self.filter_word = filter_word
        self.search = search


class NoResult:
    pass


class SoLocatorFilter(QgsLocatorFilter):

    HEADERS = {b'User-Agent': b'Mozilla/5.0 QGIS SoLocator Filter'}

    message_emitted = pyqtSignal(str, str, Qgis.MessageLevel, QWidget)

    def __init__(self, iface: QgisInterface = None):
        """"
        :param iface: QGIS interface, given when on the main thread (which will display/trigger results), None otherwise
        """
        super().__init__()

        self.iface = iface
        self.settings = Settings()

        #  following properties will only be used in main thread
        self.rubber_band = None
        self.map_canvas: QgsMapCanvas = None
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
                'filter': self.settings.enabled_dataproducts(),
                'limit': str(self.settings.value('results_limit'))

            }

            nam = NetworkAccessManager()
            feedback.canceled.connect(nam.abort)
            url = self.url_with_param(url, params)
            self.dbg_info(url)
            try:
                (response, content) = nam.request(url, headers=self.HEADERS, blocking=True)
                self.handle_response(response, search)
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

    def handle_response(self, response, search_text: str):
        try:
            if response.status_code != 200:
                if not isinstance(response.exception, RequestsExceptionUserAbort):
                    self.info("Error in main response with status code: {} from {}"
                              .format(response.status_code, response.url))
                return

            data = json.loads(response.content.decode('utf-8'))

            # sub-filtering
            # self.dbg_info(data['result_counts'])
            if len(data['result_counts']) > 1:
                for _filter in data['result_counts']:
                    result = QgsLocatorResult()
                    result.filter = self
                    result.group = 'Suche einschränken'
                    result.displayString = _filter['filterword']
                    if _filter['count']:
                        result.displayString += ' ({})'.format(_filter['count'])
                    self.dbg_info(_filter)
                    result.icon, _ = self.dataproduct2icon_description(_filter['dataproduct_id'], 'datasetview')
                    result.userData = FilterResult(_filter['filterword'], search_text)
                    self.resultFetched.emit(result)

            for res in data['results']:
                # self.dbg_info(res)

                result = QgsLocatorResult()
                result.filter = self

                if 'feature' in res.keys():
                    f = res['feature']
                    # self.dbg_info("feature: {}".format(f))
                    result.displayString = f['display']
                    result.group = 'Orte'
                    result.userData = FeatureResult(
                        dataproduct_id=f['dataproduct_id'],
                        id_field_name=f['id_field_name'],
                        id_field_type=f['id_field_type'],
                        feature_id=f['feature_id']
                    )
                    data_product = f['dataproduct_id']
                    data_type = None

                elif 'dataproduct' in res.keys():
                    dp = res['dataproduct']
                    # self.dbg_info("dataproduct: {}".format(dp))
                    result = QgsLocatorResult()
                    result.filter = self
                    result.displayString = dp['display']
                    result.group = 'Karten'
                    result.userData = DataProductResult(
                        type=dp['type'],
                        dataproduct_id=dp['dataproduct_id'],
                        display=dp['display'],
                        dset_info=dp['dset_info'],
                        sublayers=dp.get('sublayers', None)
                    )
                    data_product = 'dataproduct'
                    data_type = dp['type']

                else:
                    continue

                result.icon, result.description = self.dataproduct2icon_description(data_product, data_type)
                self.result_found = True
                self.resultFetched.emit(result)

        except Exception as e:
            self.info(str(e), Qgis.Critical)
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            filename = os.path.split(exc_traceback.tb_frame.f_code.co_filename)[1]
            self.info('{} {} {}'.format(exc_type, filename, exc_traceback.tb_lineno), Qgis.Critical)
            self.info(traceback.print_exception(exc_type, exc_obj, exc_traceback), Qgis.Critical)

    def triggerResult(self, result: QgsLocatorResult):
        # this is run in the main thread, i.e. map_canvas is not None
        self.clearPreviousResults()

        ctrl_clicked = Qt.ControlModifier == QApplication.instance().queryKeyboardModifiers()
        self.dbg_info(("CTRL pressed: {}".format(ctrl_clicked)))

        if type(result.userData) == NoResult:
            pass
        elif type(result.userData) == FilterResult:
            self.filtered_search(result.userData)
        elif type(result.userData) == FeatureResult:
            self.fetch_feature(result.userData)
        elif type(result.userData) == DataProductResult:
            self.fetch_data_product(result.userData, ctrl_clicked)
        else:
            self.info('Incorrect result. Please contact support', Qgis.Critical)

    def filtered_search(self, filter_result: FilterResult):
        search_text = '{prefix} {filter_word}: {search}'.format(
            prefix=self.activePrefix(), filter_word=filter_result.filter_word, search=filter_result.search
        )
        # Compatibility for QGIS < 3.10
        # TODO: remove
        try:
            self.iface.locatorSearch(search_text)
        except AttributeError:
            for w in self.iface.mainWindow().findChildren(QgsFilterLineEdit):
                if hasattr(w.parent(), 'search') and hasattr(w.parent(), 'invalidateResults'):
                    w.setText(search_text)
                    return
            raise NameError('Locator not found')

    def highlight(self, geometry: QgsGeometry):
        self.clearPreviousResults()
        if geometry is None:
            return

        self.rubber_band.reset(geometry.type())
        self.rubber_band.addGeometry(geometry, None)

        rect = geometry.boundingBox()
        if not self.settings.value('keep_scale'):
            if rect.isEmpty():
                current_extent = self.map_canvas.extent()
                rect = current_extent.scaled(self.settings.value('point_scale')/self.map_canvas.scale(), rect.center())
            else:
                rect.scale(4)
        self.map_canvas.setExtent(rect)
        self.map_canvas.refresh()

        self.current_timer = QTimer()
        self.current_timer.timeout.connect(self.clearPreviousResults)
        self.current_timer.setSingleShot(True)
        self.current_timer.start(5000)

    def fetch_feature(self, feature: FeatureResult):
        self.dbg_info(feature)
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

        elif geometry_type == 'MultiPolygon':
            islands = data['geometry']['coordinates']
            for i in range(0, len(islands)):
                for r in range(0, len(islands[i])):
                    for p in range(0, len(islands[i][r])):
                        islands[i][r][p] = QgsPointXY(islands[i][r][p][0], islands[i][r][p][1])
            geometry = QgsGeometry.fromMultiPolygonXY(islands)


        else:
            # SoLocator does not handle {geometry_type} yet. Please contact support
            self.info('SoLocator unterstützt den Geometrietyp {geometry_type} nicht.'
                      ' Bitte kontaktieren Sie den Support.'.format(
                geometry_type=geometry_type), Qgis.Warning
            )

        geometry.transform(self.transform_ch)
        self.highlight(geometry)

    def fetch_data_product(self, product: DataProductResult, open_dialog: bool):
        self.dbg_info(product)
        # see https://geo-t.so.ch/api/dataproduct/v1/api/
        url = 'https://geo-t.so.ch/api/dataproduct/v1/{dataproduct_id}'.format(dataproduct_id=product.dataproduct_id)
        self.nam_fetch_feature = NetworkAccessManager()
        self.dbg_info(url)
        self.nam_fetch_feature.finished.connect(self.parse_data_product_response)
        self.nam_fetch_feature.request(url, headers=self.HEADERS, blocking=False)

    def parse_data_product_response(self, response):
        if response.status_code != 200:
            if not isinstance(response.exception, RequestsExceptionUserAbort):
                self.info("Error in feature response with status code: {} from {}"
                          .format(response.status_code, response.url))
            return

        data = json.loads(response.content.decode('utf-8'))

        # # debug
        # for i, v in data.items():
        #     if i in ('qml', 'contacts'): continue
        #     if i == 'sublayers':
        #         for sublayer in data['sublayers']:
        #             for j, u in sublayer.items():
        #                 if j in ('qml', 'contacts'): continue
        #                 self.dbg_info('*** sublayer {}: {}'.format(j, u))
        #     else:
        #         self.dbg_info('*** {}: {}'.format(i, v))

        try:
            insertion_point = self.iface.layerTreeInsertionPoint()
        except AttributeError:
            # backward compatibility for QGIS < 3.10
            # TODO: remove
            insertion_point = layerTreeInsertionPoint(self.iface.layerTreeView())
        self.dbg_info("insertion point: {} {}".format(insertion_point.parent.name(), insertion_point.position))
        self.load_layer(data, insertion_point)

    def load_layer(self, data: dict, insertion_point: InsertionPoint):
        """
        Recursive method to load layers / groups
        """
        self.dbg_info("load_layer call in {} at position {}".format(insertion_point.parent.name(), insertion_point.position))
        if type(data) is list:
            for d in data:
                self.load_layer(d, insertion_point)
        else:
            # self.dbg_info('*** load: {}'.format(data.keys()))
            if data['type'] == LAYER_GROUP:
                if insertion_point.position >= 0:
                    group = insertion_point.parent.insertGroup(insertion_point.position, data['display'])
                else:
                    group = insertion_point.parent.addGroup(data['display'])

                self.load_layer(data['sublayers'], InsertionPoint(group, -1))
            else:
                self.dbg_info('*** load: {}'.format(data['wms_datasource']))
                ds = data['wms_datasource']
                if type(ds) is list and len(ds) == 1:
                    ds = ds[0]
                url = "contextualWMSLegend=0&crs={crs}&dpiMode=7&featureCount=10&format=image/png&layers={layer}&styles&url={url}".format(
                    crs=data.get('crs', DEFAULT_CRS), layer=ds['name'], url=ds['service_url']
                )
                layer = QgsRasterLayer(url, data['display'], 'wms')
                QgsProject.instance().addMapLayer(layer, False)
                self.dbg_info("inserting layer in {} at position {}".format(insertion_point.parent.name(), insertion_point.position))
                if insertion_point.position >= 0:
                    insertion_point.parent.insertLayer(insertion_point.position, layer)
                else:
                    insertion_point.parent.addLayer(layer)

                if 'postgis_datasource' in data:
                    self.dbg_info(data['postgis_datasource'])

    def info(self, msg="", level=Qgis.Info, emit_message: bool = False):
        self.logMessage(str(msg), level)
        if emit_message:
            self.message_emitted.emit(msg, level)

    def dbg_info(self, msg=""):
        if DEBUG:
            self.info(msg)

    def dataproduct2icon_description(self, dataproduct: str, type: str) -> QIcon:

        label = None
        icon = QIcon(":/plugins/solocator/icons/solocator.png")

        if dataproduct == 'dataproduct':
            if type == LAYER_GROUP:
                label = 'Layergruppe'
                icon = QIcon(":/plugins/solocator/icons/results/layergroup_open.svg")
            else:
                label = DATAPRODUCT_TYPE_TRANSLATION[type]
                icon = QIcon(":/plugins/solocator/icons/results/ebene.svg")

        elif dataproduct.startswith('ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge'):
            label = 'Adresse'
            icon = QIcon(":/plugins/solocator/icons/results/adresse.svg")

        elif dataproduct.startswith('ch.so.agi.gemeindegrenzen'):
            label = 'Gemeinde'
            icon = QIcon(":/plugins/solocator/icons/results/gemeinde.svg")

        elif dataproduct.startswith('ch.so.agi.av.bodenbedeckung'):
            label = 'Gebäude (EGID)'
            icon = QIcon(":/plugins/solocator/icons/results/ort_punkt.svg")

        elif dataproduct.startswith('ch.so.agi.av.grundstuecke.projektierte'):
            label = 'Grundstück projektiert'
            icon = QIcon(":/plugins/solocator/icons/results/grundstuecke.svg")

        elif dataproduct.startswith('ch.so.agi.av.grundstuecke.rechtskraeftig'):
            label = 'Grundstück rechtskräftig'
            icon = QIcon(":/plugins/solocator/icons/results/grundstuecke.svg")

        elif dataproduct.startswith('ch.so.agi.av.nomenklatur.flurnamen'):
            label = 'Flurname'
            icon = QIcon(":/plugins/solocator/icons/results/gelaende_flurname.svg")

        elif dataproduct.startswith('ch.so.agi.av.nomenklatur.gelaendename'):
            label = 'Geländename'
            icon = QIcon(":/plugins/solocator/icons/results/gelaende_flurname.svg")

        return icon, label



