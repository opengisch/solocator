from enum import Enum


class LoadingMode(Enum):
    PG = 1
    WMS = 2

    def __str__(self):
        if self.value == LoadingMode.PG.value:
            return 'PostgreSQL'
        elif self.value == LoadingMode.WMS.value:
            return 'WMS'
        else:
            return self.name

    def alternate_mode(self):
        if self.value == LoadingMode.PG.value:
            return LoadingMode.WMS
        elif self.value == LoadingMode.WMS.value:
            return LoadingMode.PG
        else:
            raise NameError('incomplete handling of enum values')