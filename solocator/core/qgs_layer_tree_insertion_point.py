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


class InsertionPoint:
    def __init__(self, group: QgsLayerTreeGroup, position: int):
        self._group = group
        self._position = position

    @property
    def group(self):
        return self._group

    @property
    def position(self):
        return self._position


def layerTreeInsertionPoint(tree_view: QgsLayerTreeView) -> tuple:
    """
    Direct copy of the code QgisApp::layerTreeInsertionPoint for QGIS < 3.10
    """
    insert_group = tree_view.layerTreeModel().rootGroup()
    current = tree_view.currentIndex()
    index = 0

    if current.isValid():

        index = current.row()

        current_node = tree_view.currentNode()
        if current_node:

            # if the insertion point is actually a group, insert new layers into the group
            if QgsLayerTree.isGroup(current_node):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = firstGroupWithoutCustomProperty(current_node, "embedded")

                return InsertionPoint(insert_group, 0)

            # otherwise just set the insertion point in front of the current node
            parent_node = current_node.parent()
            if QgsLayerTree.isGroup(parent_node):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = firstGroupWithoutCustomProperty(parent_node, "embedded")
                if parent_node != insert_group:
                    index = 0

    return InsertionPoint(insert_group, index)


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

