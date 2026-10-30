PLUGIN_NAME=        zapret2-restyle
PLUGIN_VERSION!=    /bin/cat ${.CURDIR}/VERSION
PLUGIN_REVISION=    13
PLUGIN_COMMENT=     Native zapret2 DPI bypass plugin for OPNsense
PLUGIN_MAINTAINER=  tolian82IPB@gmail.com
.include "${.CURDIR}/src/opnsense/scripts/OPNsense/Zapret/python_runtime.conf"
PLUGIN_DEPENDS=     ${ZAPRET_PYTHON_PACKAGE}
PLUGIN_LICENSE=     MIT
.include "../../Mk/plugins.mk"
