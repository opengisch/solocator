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


from qgis.core import QgsLayerTree, QgsLayerTreeGroup
from qgis.gui import QgsLayerTreeView

from solocator.core.utils import dbg_info


def firstGroupWithoutCustomProperty(group: QgsLayerTreeGroup, _property: str) -> QgsLayerTreeGroup:
    """
    Taken from QgsLayerTreeUtils::firstGroupWithoutCustomProperty
    :param group:
    :param _property:
    :return:
    """
    # if the group is embedded go to the first non-embedded group, at worst the top level item
    while group.customProperty(_property):
        if not group.parent():
            break
        if QgsLayerTree.isGroup(group.parent()):
            group = group.parent()
        else:
            dbg_info(group)
            assert False

    return group

