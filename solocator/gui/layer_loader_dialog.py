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
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QAbstractItemView, QMessageBox, QTreeWidgetItem
from qgis.PyQt.uic import loadUiType

from solocator.qgis_setting_manager import SettingDialog, UpdateMode
from solocator.core.settings import Settings
from solocator.core.layer import SoLayer, LoadingOptions

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/layer_loader_dialog.ui'))


class LayerLoaderDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, data, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        self.layerTreeWidget.addTopLevelItem(data.tree_widget_item())
        self.layerTreeWidget.setColumnCount(1)
        self.layerTreeWidget.setHeaderLabels(['Name'])
        self.layerTreeWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.layerTreeWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.layerTreeWidget.expandAll()
        self.layerTreeWidget.setCurrentItem(self.layerTreeWidget.topLevelItem(0))
        self.layerTreeWidget.itemChanged.connect(self.on_item_changed)
        self.layerTreeWidget.itemSelectionChanged.connect(self.on_selection_changed)
        self.on_selection_changed()

        self.settings = settings
        self.init_widgets()

        self.setting_widget('wms_image_format').auto_populate()

    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        # we assume any change is a check state change
        if column == 0:
            self.layerTreeWidget.itemChanged.disconnect(self.on_item_changed)
            LayerLoaderDialog.check_children(item, item.checkState(0))
            # if there is any parent checked, we should check the connecting items
            if item.checkState(0) == Qt.Checked:
                LayerLoaderDialog.safe_check_parent(item)
            self.layerTreeWidget.itemChanged.connect(self.on_item_changed)

    @staticmethod
    def check_children(item: QTreeWidgetItem, check_state: Qt.CheckStateRole):
        item.setCheckState(0, check_state)
        item.data(0, Qt.UserRole).loaded = check_state == Qt.Checked
        for i in range(0, item.childCount()):
            child = item.child(i)
            LayerLoaderDialog.check_children(child, check_state)

    @staticmethod
    def safe_check_parent(item):
        has_checked_parent = False
        parent = item.parent()
        while parent:
            if parent.checkState(0) == Qt.Checked:
                has_checked_parent = True
                break
            parent = parent.parent()
        if has_checked_parent:
            parent = item.parent()
            while parent:
                if parent.checkState(0) == Qt.Checked:
                    # stop when needed
                    break
                parent.setCheckState(0, Qt.Checked)
                item.data(0, Qt.UserRole).loaded = True
                parent = parent.parent()

    def on_selection_changed(self):
        current_item = self.layerTreeWidget.currentItem().data(0, Qt.UserRole)
        if type(current_item) == SoLayer:
            self.descriptionBrowser.setText(current_item.description)
        else:
            self.descriptionBrowser.clear()

    def layers(self):
        # we assume there is only 1 top level item
        return LayerLoaderDialog.top_checked_layers(self.layerTreeWidget.topLevelItem(0))

    @staticmethod
    def top_checked_layers(item):
        layers = []
        for i in range(0, item.childCount()):
            child = item.child(i)
            if child.checkState(0) == Qt.Checked:
                layers.append(child.data(0, Qt.UserRole))
            else:
                layers.extend(LayerLoaderDialog.top_checked_layers(child))
        return layers

    def loading_options(self) -> LoadingOptions:
        return LoadingOptions(self.wms_load_separate.isChecked(), self.wms_image_format.currentText(),
                              self.load_as_postgres.isChecked(), self.pg_auth_id.configId())

    def accept(self) -> None:
        if self.load_as_postgres.isChecked() and self.pg_auth_id.configId() == '':
            button = QMessageBox.question(self, 'Posgres authentification',
                                          'No authentification method has been defined. Are you sure to continue?')
            if button == QMessageBox.Yes:
                QDialog.accept(self)
            else:
                return
        else:
            QDialog.accept(self)
