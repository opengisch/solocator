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

from solocator.qgis_setting_manager import SettingManager, Scope, Bool, Stringlist, Integer, Double, String, EnumType, Enum
from solocator.core.loading_mode import LoadingMode

pluginName = "solocator"


class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)

        self.add_setting(Integer('results_limit', Scope.Global, 20))
        self.add_setting(Bool('keep_scale', Scope.Global, False))
        self.add_setting(Double('point_scale', Scope.Global, 1000))
        self.add_setting(Enum('default_layer_loading_mode', Scope.Global, LoadingMode.PG, enum_type=EnumType.Python))

        self.add_setting(Bool('wms_load_separate', Scope.Global, True))
        self.add_setting(String('wms_image_format', Scope.Global, 'png', allowed_values=('png', 'jpeg')))

        self.add_setting(String('pg_auth_id', Scope.Global, None))

        # these settings should be empty, but can be overwritten for testing purpose
        self.add_setting(String('pg_service', Scope.Global, ''))
        self.add_setting(String('pg_host', Scope.Global, ''))
        self.add_setting(String('service_url', Scope.Global, ''))

        # save only skipped categories so newly added categories will be enabled by default
        self.add_setting(Stringlist('skipped_dataproducts', Scope.Global, None))


DEFAULT_PG_HOST = 'geodb.rootso.org'
DEFAULT_PG_SERVICE = 'pub'

PG_SERVICE = Settings().value('pg_service') or DEFAULT_PG_SERVICE
PG_HOST = Settings().value('pg_host') or DEFAULT_PG_HOST
PG_DB = 'pub'
PG_PORT = '5432'

DEFAULT_BASE_URL = 'https://geo-i.so.ch/api'
BASE_URL = Settings().value('service_url') or DEFAULT_BASE_URL
SEARCH_URL = '{}/search/v2'.format(BASE_URL)  # see https://geo-t.so.ch/api/search/v2/api/
FEATURE_URL = '{}/data/v1'.format(BASE_URL)  # see https://geo-t.so.ch/api/data/v1/api/
DATA_PRODUCT_URL = '{}/dataproduct/v1'.format(BASE_URL)  # see https://geo-t.so.ch/api/dataproduct/v1/api/

