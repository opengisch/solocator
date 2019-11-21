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

from PyQt5.QtGui import QIcon

DATA_PRODUCTS = {'foreground': 'Karten',
                 'background': 'Hintergrundkarten',
                 'ch.so.agi.gemeindegrenzen': 'Gemeinden',
                 'ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge': 'Adressen',
                 'ch.so.agi.av.bodenbedeckung': 'Gebäude (EGID)',
                 'ch.so.agi.av.grundstuecke.projektierte': 'Grundstücke projektiert',
                 'ch.so.agi.av.grundstuecke.rechtskraeftig': 'Grundstücke rechtskräftig',
                 'ch.so.agi.av.nomenklatur.flurnamen': 'Flurnamen',
                 'ch.so.agi.av.nomenklatur.gelaendenamen': 'Geländenamen'}


DATAPRODUCT_TYPE_TRANSLATION = {
    'datasetview': 'Layer',
    'facadelayer': 'Fassadenlayer',
    'background': 'Hintergrundlayer'
}

LAYER_GROUP = 'layergroup'
FACADE_LAYER = 'facadelayer'


def dataproduct2icon_description(data_product: str, layer_type: str) -> QIcon:
    label = None
    icon = QIcon(":/plugins/solocator/icons/solocator.png")

    if data_product == 'dataproduct':
        if layer_type == LAYER_GROUP:
            label = 'Layergruppe'
            icon = QIcon(":/plugins/solocator/icons/results/ebene.svg")
        else:
            label = DATAPRODUCT_TYPE_TRANSLATION[layer_type]
            icon = QIcon(":/plugins/solocator/icons/results/einzel-ebene.svg")

    elif data_product.startswith('ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge'):
        label = 'Adresse'
        icon = QIcon(":/plugins/solocator/icons/results/adresse.svg")

    elif data_product.startswith('ch.so.agi.gemeindegrenzen'):
        label = 'Gemeinde'
        icon = QIcon(":/plugins/solocator/icons/results/gemeinde.svg")

    elif data_product.startswith('ch.so.agi.av.bodenbedeckung'):
        label = 'Gebäude (EGID)'
        icon = QIcon(":/plugins/solocator/icons/results/ort_punkt.svg")

    elif data_product.startswith('ch.so.agi.av.grundstuecke.projektierte'):
        label = 'Grundstück projektiert'
        icon = QIcon(":/plugins/solocator/icons/results/grundstuecke.svg")

    elif data_product.startswith('ch.so.agi.av.grundstuecke.rechtskraeftig'):
        label = 'Grundstück rechtskräftig'
        icon = QIcon(":/plugins/solocator/icons/results/grundstuecke.svg")

    elif data_product.startswith('ch.so.agi.av.nomenklatur.flurnamen'):
        label = 'Flurname'
        icon = QIcon(":/plugins/solocator/icons/results/gelaende_flurname.svg")

    elif data_product.startswith('ch.so.agi.av.nomenklatur.gelaendename'):
        label = 'Geländename'
        icon = QIcon(":/plugins/solocator/icons/results/gelaende_flurname.svg")

    return icon, label


def image_format_force_jpeg(name: str, is_background: str):
    if 'orthofoto' in name.lower() or is_background:
        return True
    else:
        return False
