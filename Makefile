PLUGIN_NAME=        zapret2-restyle
PLUGIN_VERSION!=    /bin/cat ${.CURDIR}/VERSION
PLUGIN_REVISION=    6
PLUGIN_COMMENT=     Native zapret2 DPI bypass plugin for OPNsense
PLUGIN_MAINTAINER=  tolian82IPB@gmail.com

# Runtime/build prerequisites are installed by this project's setup logic.
# They are not declared here because availability may differ between
# supported OPNsense package repositories.
PLUGIN_DEPENDS=
PLUGIN_LICENSE=     MIT

.include "../../Mk/plugins.mk"
