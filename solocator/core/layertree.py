
from qgis.core import QgsLayerTree, QgsLayerTreeUtils
from qgis.gui import QgisInterface


def layerTreeInsertionPoint(iface: QgisInterface) -> tuple:
    """
    Direct copy of the code QgisApp::layerTreeInsertionPoint for QGIS < 3.10
    """
    insert_group = iface.layerTreeView().layerTreeModel().rootGroup()
    current = iface.layerTreeView().currentIndex()
    index = 0

    if current.isValid():

        index = current.row()

        currentNode = iface.layerTreeView().currentNode()
        if currentNode:

            # if the insertion point is actually a group, insert new layers into the group
            if QgsLayerTree.isGroup(currentNode):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = QgsLayerTreeUtils.firstGroupWithoutCustomProperty(currentNode, "embedded")

                return insert_group, 0

            # otherwise just set the insertion point in front of the current node
            parentNode = currentNode.parent()
            if QgsLayerTree.isGroup(parentNode):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = QgsLayerTreeUtils.firstGroupWithoutCustomProperty(parentNode, "embedded")
                if parentNode != insert_group:
                    index = 0

    return insert_group, index
