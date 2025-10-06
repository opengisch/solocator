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

import os
from qgis.PyQt.QtGui import QIcon

from solocator import PLUGIN_DIR
from solocator.core.utils import dbg_info

DATA_PRODUCTS = {'foreground': 'Karten',
                 'background': 'Hintergrundkarten',
                 'ch.so.agi.gemeindegrenzen': 'Gemeinden',
                 'ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge': 'Adressen',
                 'ch.so.agi.av.bodenbedeckung': 'Gebäude (EGID)',
                 'ch.so.agi.av.grundstuecke.projektierte': 'Grundstücke projektiert',
                 'ch.so.agi.av.grundstuecke.rechtskraeftig': 'Grundstücke rechtskräftig',
                 'ch.so.agi.av.nomenklatur.flurnamen': 'Flurnamen',
                 'ch.so.agi.av.nomenklatur.gelaendenamen': 'Geländenamen'}


LAYER_GROUP = 'layergroup'
SINGLE_ACTOR = 'singleactor'
FACADE_LAYER = 'facadelayer'

DATAPRODUCT_TYPE_TRANSLATION = {
    LAYER_GROUP: 'Layergruppe',
    SINGLE_ACTOR: 'Layer'
}


def dataproduct2icon_description(data_product: str, layer_type: str | None) -> QIcon:
    """
    Returns an icon for a given data product
    :param data_product:
    :param layer_type:
    :return: The QIcon
    """
    label = None
    icon = QIcon(str(os.path.join(PLUGIN_DIR, "icons", "solocator.png")))

    if data_product == 'dataproduct':
        label = DATAPRODUCT_TYPE_TRANSLATION[layer_type]
        if layer_type == LAYER_GROUP:
            icon = QIcon(get_result_icon_path("ebene.svg"))
        else:
            icon = QIcon(get_result_icon_path("einzel-ebene.svg"))

    elif data_product.startswith('ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge'):
        label = 'Adresse'
        icon = QIcon(get_result_icon_path("adresse.svg"))

    elif data_product.startswith('ch.so.agi.gemeindegrenzen'):
        label = 'Gemeinde'
        icon = QIcon(get_result_icon_path("gemeinde.svg"))

    elif data_product.startswith('ch.so.agi.av.bodenbedeckung'):
        label = 'Gebäude (EGID)'
        icon = QIcon(get_result_icon_path("ort_punkt.svg"))

    elif data_product.startswith('ch.so.agi.av.grundstuecke.projektierte'):
        label = 'Grundstück projektiert'
        icon = QIcon(get_result_icon_path("grundstuecke.svg"))

    elif data_product.startswith('ch.so.agi.av.grundstuecke.rechtskraeftig'):
        label = 'Grundstück rechtskräftig'
        icon = QIcon(get_result_icon_path("grundstuecke.svg"))

    elif data_product.startswith('ch.so.agi.av.nomenklatur.flurnamen'):
        label = 'Flurname'
        icon = QIcon(get_result_icon_path("gelaende_flurname.svg"))

    elif data_product.startswith('ch.so.agi.av.nomenklatur.gelaendename'):
        label = 'Geländename'
        icon = QIcon(get_result_icon_path("gelaende_flurname.svg"))

    return icon, label


def get_result_icon_path(file_name: str) -> str:
    """
    Returns the absolute path of an icon file in the results folder
    Args:
        file_name: icon file name

    Returns: Absolute path to of the icon file as string

    """
    return str(os.path.join(PLUGIN_DIR, "icons", "results", file_name))


def image_format_force_jpeg(name: str, is_background: str) -> bool:
    """
    Returns True if the WMS layer should use JPEG as image format (discarding the user preference)
    :param name:
    :param is_background:
    """
    if 'orthofoto' in name.lower() or is_background:
        return True
    else:
        return False


def force_wms(data: dict, is_background: bool) -> bool:
    """
    Determines if the layer should be forced as WMS (discarding the user preference)
    :param data:
    :param is_background:
    :return: True if it should load as WMS
    """
    # always load background as WMS
    if is_background:
        return True
    # if a child has no PG info, load as WMS
    missing_pg_source = missing_postgis_datasource(data)
    if missing_pg_source:
        dbg_info('forcing WMS due to missing PG data source')
    return missing_pg_source


def missing_postgis_datasource(data: dict):
    if hasattr(data, 'children'):
        # is a SoGroup
        for child in data.children:
            if missing_postgis_datasource(child):
                return True
        return False
    else:
        # must be a SoLayer
        if data.postgis_datasource is None:
            return True
        else:
            return False


