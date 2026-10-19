<?php

/**
 * Resolve Zapret sidebar labels in the OPNsense menu builder, not in
 * page-specific JavaScript.  The menu is rebuilt for every web request,
 * including non-Zapret pages, breadcrumbs and the menu search API.
 */
namespace OPNsense\Zapret\Menu;

use OPNsense\Base\Menu\MenuContainer;
use OPNsense\Core\Config;

class Menu extends MenuContainer
{
    public function collect()
    {
        $config = Config::getInstance()->object();
        $language = trim((string)($config->system->language ?? 'en_US'));

        // Match OPNsense ControllerRoot::setLang(): a user's selected language
        // takes precedence over the global Web GUI language.
        if (!empty($_SESSION['Username'])) {
            foreach ($config->system->user as $user) {
                if ((string)$user->name === (string)$_SESSION['Username']) {
                    if (trim((string)$user->language) !== '') {
                        $language = trim((string)$user->language);
                    }
                    break;
                }
            }
        }

        // All other locales continue to use Menu.xml and OPNsense gettext.
        if (!preg_match('/^ru(?:[_\-.]|$)/i', $language)) {
            return;
        }

        foreach ([
            'General' => 'Стратегия',
            'Voice' => 'Передача голоса',
            'Diagnostics' => 'Лаборатория',
        ] as $id => $label) {
            // FixedName is the supported MenuItem setter for labels that
            // should not depend on the system-wide OPNsense.mo catalog.
            $this->appendItem('Services.Zapret', $id, ['FixedName' => $label]);
        }
    }
}
