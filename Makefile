PLUGIN_NAME=        zapret2-restyle
PLUGIN_VERSION=     0.1.0
PLUGIN_REVISION=    1
PLUGIN_COMMENT=     Native zapret2 DPI bypass plugin for OPNsense
PLUGIN_MAINTAINER=  tolian82IPB@gmail.com

# External build dependencies are installed by setup.sh when required.
# They are not declared here because they may not exist in the default
# OPNsense package repository on a fresh installation.
PLUGIN_DEPENDS=
PLUGIN_LICENSE=     MIT

.include "../../Mk/plugins.mk"
