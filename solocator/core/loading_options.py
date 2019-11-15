from solocator.core.loading_mode import LoadingMode


class LoadingOptions:
    """
    A class to hold the loading options
    """
    def __init__(self, wms_load_separate: bool, wms_image_format: str,
                 loading_mode: LoadingMode, pg_auth_id: str = None, pg_service: str = None):
        """
        :param wms_load_separate: If True, individual layers will be loaded as separate instead of a single one
        :param wms_image_format: image format
        :param loading_mode: the LoadingMode (WMS or PostgreSQL)
        :param pg_auth_id: the configuration ID for the authentification
        :param pg_service: the PG service nate
        """
        self.loading_mode = loading_mode
        self.wms_load_separate = wms_load_separate
        self.pg_auth_id = pg_auth_id
        self.pg_service = pg_service
        self.wms_image_format = wms_image_format