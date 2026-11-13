PLUGIN_NAME=        zapret2-restyle
PLUGIN_VERSION!=    /bin/cat ${.CURDIR}/VERSION
PLUGIN_REVISION=    23
PLUGIN_COMMENT=     Native zapret2 DPI bypass plugin for OPNsense
PLUGIN_MAINTAINER=  tolian82IPB@gmail.com
PLUGIN_DEPENDS=     python${PLUGIN_PYTHON} gmake pkgconf luajit git jq ca_root_nss py${PLUGIN_PYTHON}-idna
PLUGIN_LICENSE=     MIT
.include "../../Mk/plugins.mk"
