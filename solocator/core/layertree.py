
from qgis.core import QgsLayerTree, QgsLayerTreeGroup, QgsLayerTreeUtils
from qgis.gui import QgsLayerTreeView


class InsertionPoint:
    def __init__(self, parent: QgsLayerTreeGroup, position: int):
        self._parent = parent
        self._position = position

    @property
    def parent(self):
        return self._parent

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
                insert_group = QgsLayerTreeUtils.firstGroupWithoutCustomProperty(current_node, "embedded")

                return InsertionPoint(insert_group, 0)

            # otherwise just set the insertion point in front of the current node
            parentNode = current_node.parent()
            if QgsLayerTree.isGroup(parentNode):

                # if the group is embedded go to the first non-embedded group, at worst the top level item
                insert_group = QgsLayerTreeUtils.firstGroupWithoutCustomProperty(parentNode, "embedded")
                if parentNode != insert_group:
                    index = 0

    return InsertionPoint(insert_group, index)
