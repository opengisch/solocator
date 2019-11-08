

## Suche für Geodaten Kanton Solothurn

Integration in die QGIS Suche für dieGeodateninfrastruktur im Kanton Solothurn. Über dieses Plugin können Layer, Flurnamen, Adressen und andere Objekte im Kanton Solothurn gesucht und lokalisiert werden.

### Install

https://github.com/opengisch/solocator/releases/latest/download/plugins.xml

### Advanced settings for testing purpose

In QGIS preferences, under advanced settings:
* Service URL: plugins/solocator/service_url (leave empty to use default)
* PostgreSQL service: plugins/solocator/pg_service (leave empty to use default, if given it should contain the DB name) 
* PostgreSQL hostname: plugins/solocator/pg_host (leave empty to use default) 

### API

* https://geo-t.so.ch/api/search/v2/api/
* https://geo-t.so.ch/api/dataproduct/v1/api/
* https://geo-t.so.ch/api/data/v1/api