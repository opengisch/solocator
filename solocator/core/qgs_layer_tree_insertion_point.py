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


from qgis.core import QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeUtils
from qgis.gui import QgsLayerTreeView


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


def layerTreeInsertionPoint(treeView: QgsLayerTreeView) -> tuple:
    """
    Direct copy of the code QgisApp::layerTreeInsertionPoint for QGIS < 3.10
    """
    insert_group = treeView.layerTreeModel().rootGroup()
    current = treeView.currentIndex()
    index = 0

    if current.isValid():

        index = current.row()

        current_node = treeView.currentNode()
        if current_node:

            # if the insertion point is actually a group, insert new layers into the group
            if QgsLayerTree.isGroup(current_node):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = firstGroupWithoutCustomProperty(current_node, "embedded")

                return InsertionPoint(insert_group, 0)

            # otherwise just set the insertion point in front of the current node
            parentNode = current_node.parent()
            if QgsLayerTree.isGroup(parentNode):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = QgsLayerTreeUtils.firstGroupWithoutCustomProperty(parentNode, "embedded")
                if parentNode != insert_group:
                    index = 0

    return InsertionPoint(insert_group, index)


def firstGroupWithoutCustomProperty(group: QgsLayerTreeGroup, property: str) -> QgsLayerTreeGroup:
    """
    Taken from QgsLayerTreeUtils::firstGroupWithoutCustomProperty
    :param group:
    :param property:
    :return:
    """
    # if the group is embedded go to the first non-embedded group, at worst the top level item
    while group.customProperty(property):
        if not group.parent():
            break

    if QgsLayerTree.isGroup(group.parent()):
        group = group.parent()
    else:
        assert False

    return group

