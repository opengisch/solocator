# -*- coding': 'utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Swiss Locator Plugin
# Copyright (C) 2018 Denis Rouzaud
#
# -----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# ---------------------------------------------------------------------

from solocator.settingmanager import SettingManager, Scope, Bool, String, Stringlist, Integer, Enum, Dictionary

pluginName = "solocator"


class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)

        self.add_setting(Integer('limit', Scope.Global, 20))

        self.add_setting(Dictionary('categories', Scope.Global,
                                    {'dataproduct': 'Karten & Geodaten',
                                     'ch.so.agi.gemeindegrenzen': 'Gemeinden',
                                     'ch.so.agi.av.gebaeudeadressen.gebaeudeeingaenge': 'Adressen',
                                     'ch.so.agi.av.bodenbedeckung': 'Bodenbedeckungsnamen',
                                     'ch.so.agi.av.grundstuecke.projektierte': 'Grundstücke projektiert',
                                     'ch.so.agi.av.grundstuecke.rechtskraeftig': 'Grundstücke rechtskräftig',
                                     'ch.so.agi.av.nomenklatur.flurnamen': 'Flurnamen',
                                     'ch.so.agi.av.nomenklatur.gelaendenamen': 'Geländenamen'}))

        # save only skipped categories so newly added categories will be enabled by default
        self.add_setting(Stringlist('skipped_categories', Scope.Global, None))

    def enabled_categories(self):
        categories = self.value('categories').keys()
        skipped = self.value('skipped_categories')
        return ','.join(list(filter(lambda id: id not in skipped, categories)))






