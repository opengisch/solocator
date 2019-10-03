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


from solocator.settingmanager import SettingManager, Scope, Bool, Stringlist, Integer, Double

pluginName = "solocator"


class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)

        self.add_setting(Integer('results_limit', Scope.Global, 20))
        self.add_setting(Bool('keep_scale', Scope.Global, False))
        self.add_setting(Double('point_scale', Scope.Global, 1000))
        self.add_setting(Bool('load_as_postgres', Scope.Global, False))

        # save only skipped categories so newly added categories will be enabled by default
        self.add_setting(Stringlist('skipped_dataproducts', Scope.Global, None))






