<?php

/**
 * Exercise the OPNsense MenuContainer entrypoint without a live firewall.
 * Verify global/per-user language precedence and independent page rendering.
 */
declare(strict_types=1);

namespace OPNsense\Core {
    class Config
    {
        public static object $current;
        public static function getInstance(): self
        {
            return new self();
        }
        public function object(): object
        {
            return self::$current;
        }
    }
}

namespace OPNsense\Base\Menu {
    class MenuContainer
    {
        public array $overrides = [];
        public function appendItem($root, $id, $properties)
        {
            $this->overrides[$root . '.' . $id] = $properties;
        }
    }
}

namespace {
    require_once __DIR__ . '/../src/opnsense/mvc/app/models/OPNsense/Zapret/Menu/Menu.php';

    function check(bool $condition, string $reason): void
    {
        if (!$condition) {
            fwrite(STDERR, 'FAIL: ' . $reason . PHP_EOL);
            exit(1);
        }
    }

    function collectLabels(string $global, ?string $user, ?string $username): array
    {
        \OPNsense\Core\Config::$current = (object)[
            'system' => (object)[
                'language' => $global,
                'user' => [(object)['name' => 'alice', 'language' => $user ?? '']],
            ],
        ];
        $_SESSION = $username === null ? [] : ['Username' => $username];
        $menu = new \OPNsense\Zapret\Menu\Menu();
        $menu->collect();
        return $menu->overrides;
    }

    $ru = [
        'Services.Zapret.General' => ['FixedName' => 'Стратегия'],
        'Services.Zapret.Voice' => ['FixedName' => 'Передача голоса'],
        'Services.Zapret.Diagnostics' => ['FixedName' => 'Лаборатория'],
    ];
    check(collectLabels('ru_RU', null, null) === $ru, 'Russian system language must translate on the first page load');
    check(collectLabels('en_US', 'ru_RU', 'alice') === $ru, 'Russian per-user language must take precedence');
    check(collectLabels('ru_RU', 'en_US', 'alice') === [], 'English per-user language must override global Russian');
    check(collectLabels('ru_RU', 'en_US', 'bob') === $ru, 'Other users must not change current language');
    check(collectLabels('en_US', null, null) === [], 'English menu must remain original Menu.xml');
    check(collectLabels('de_DE', null, null) === [], 'Other language menus must remain gettext-driven');
    check(collectLabels('ru-RU', null, null) === $ru, 'Hyphenated Russian locale must work');
    check(collectLabels('ru_RU.UTF-8', null, null) === $ru, 'Russian locale with codeset must work');

    $root = __DIR__ . '/../src/opnsense/mvc/app/views/OPNsense/Zapret/';
    foreach (['general.volt', 'voice.volt', 'diagnostics.volt'] as $name) {
        $view = file_get_contents($root . $name);
        check(strpos($view, '$(' . "'a[href=\\\"/ui/zapret") === false,
              $name . ' must not patch sidebar labels in page JS');
        check(!preg_match('/\$\([\x27\x22]a\[href=[^\r\n]*?\)\.text\(/', $view),
              $name . ' must not mutate OPNsense navigation labels');
    }

    echo "PASS: native MenuContainer translates Zapret sidebar on all pages with per-user locale precedence\n";
}
