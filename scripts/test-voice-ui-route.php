<?php

/**
 * Exercise the real OPNsense 26.7 Router::routeRequest/parsePath/resolveNamespace
 * against plugin source or an extracted installable package.
 *
 * Router fixture: opnsense/core stable/26.7, unmodified BSD-2-Clause source.
 * The AppConfig/Dispatcher/Request/Session/Response stubs isolate framework I/O;
 * path decoding and controller-file lookup are NOT emulated.
 *
 * Usage: php scripts/test-voice-ui-route.php [src/opnsense|extracted/usr/local/opnsense]
 */
declare(strict_types=1);

namespace OPNsense\Core {
    class AppConfig
    {
        public object $application;
        public function __construct()
        {
            $this->application = (object)[
                'controllersDir' => [getenv('ZAPRET_UI_CONTROLLERS_DIR')]
            ];
        }
    }
}

namespace OPNsense\Base {
    class RouteTestView
    {
        public string $picked = '';
        public mixed $voiceForm = null;
        public mixed $generalForm = null;
        public function pick(string $name): void
        {
            $this->picked = $name;
        }
    }
    class IndexController
    {
        public RouteTestView $view;
        public function __construct()
        {
            $this->view = new RouteTestView();
        }
        protected function getForm(string $name): string
        {
            return $name;
        }
    }
}

namespace OPNsense\Mvc\Exceptions {
    class InvalidUriException extends \RuntimeException {}
}

namespace OPNsense\Mvc {
    class Request {}
    class Session {}
    class Response {}
    class Dispatcher
    {
        public static array $last = [];
        public function __construct(
            private string $namespace,
            private string $controller,
            private string $action,
            private array $parameters
        ) {}
        public function dispatch(Request $request, Response $response, Session $session): void
        {
            $classname = $this->namespace . '\\' . $this->controller;
            if (!class_exists($classname) || !method_exists($classname, $this->action)) {
                throw new \RuntimeException("Unresolvable UI controller/action: " . $classname . '::' . $this->action);
            }
            $instance = new $classname();
            $action = $this->action;
            $instance->$action(...$this->parameters);
            self::$last = [
                'class' => $classname,
                'action' => $action,
                'view' => $instance->view->picked,
                'form' => $instance->view->voiceForm ?? $instance->view->generalForm,
            ];
        }
    }
}

namespace {
    use OPNsense\Mvc\Router;
    use OPNsense\Mvc\Dispatcher;
    use OPNsense\Mvc\Exceptions\InvalidUriException;

    function check(bool $condition, string $message): void
    {
        if (!$condition) {
            fwrite(STDERR, "FAIL: " . $message . PHP_EOL);
            exit(1);
        }
    }

    $pluginRoot = realpath($argv[1] ?? (__DIR__ . '/../src/opnsense'));
    check($pluginRoot !== false, 'Plugin tree does not exist');
    $app = $pluginRoot . '/mvc/app';
    $controllers = $app . '/controllers';
    $menuPath = $app . '/models/OPNsense/Zapret/Menu/Menu.xml';
    $aclPath = $app . '/models/OPNsense/Zapret/ACL/ACL.xml';
    $formPath = $controllers . '/OPNsense/Zapret/forms/voice.xml';
    $viewPath = $app . '/views/OPNsense/Zapret/voice.volt';
    foreach ([$menuPath, $aclPath, $formPath, $viewPath] as $path) {
        check(is_file($path), 'Required installed Voice resource missing: ' . $path);
    }
    $menu = file_get_contents($menuPath);
    $acl = file_get_contents($aclPath);
    check(str_contains($acl, 'ui/zapret/*'), 'Voice page missing ACL coverage');

    // Inspect the REAL Menu.xml targets, not hard-coded URLs alone.
    $expected = [
        'General' => ['/ui/zapret', 'IndexController', 'OPNsense/Zapret/general', 'general'],
        'Voice' => ['/ui/zapret/voice', 'VoiceController', 'OPNsense/Zapret/voice', 'voice'],
        'Diagnostics' => ['/ui/zapret/diagnostics', 'DiagnosticsController', 'OPNsense/Zapret/diagnostics', null],
    ];

    require_once __DIR__ . '/fixtures/opnsense-26.7/Router.php';
    foreach (['IndexController', 'DiagnosticsController', 'VoiceController'] as $name) {
        $path = $controllers . '/OPNsense/Zapret/' . $name . '.php';
        if (is_file($path)) {
            require_once $path;
        }
    }

    putenv('ZAPRET_UI_CONTROLLERS_DIR=' . $controllers);
    $router = new Router('/ui/');
    foreach ($expected as $name => [$uri, $controller, $view, $form]) {
        check(preg_match('~<' . $name . '\b[^>]*\burl="([^"]+)"~', $menu, $matches) === 1,
              'Missing ' . $name . ' menu URL');
        check($matches[1] === $uri, 'Unexpected ' . $name . ' menu URL: ' . $matches[1]);
        try {
            $router->routeRequest($matches[1], [
                'controller' => 'IndexController',
                'action' => 'indexAction',
            ]);
        } catch (\Throwable $e) {
            check(false, $name . ' menu URL cannot be routed: ' . $e->getMessage());
        }
        $actual = Dispatcher::$last;
        check($actual['class'] === 'OPNsense\\Zapret\\' . $controller,
              $name . ' menu resolves the wrong controller');
        check($actual['action'] === 'indexAction', $name . ' menu resolves the wrong action');
        check($actual['view'] === $view, $name . ' controller does not pick the expected view');
        check($actual['form'] === $form, $name . ' controller does not bind the expected form');
        check(is_file($app . '/views/' . $view . '.volt'), $name . ' Volt view missing');
        if ($form !== null) {
            check(is_file($controllers . '/OPNsense/Zapret/forms/' . $form . '.xml'),
                  $name . ' form missing');
        }
    }

    // Reproduce the _194 defect with the same Router, not a hand-written route parser.
    $absentRoot = sys_get_temp_dir() . '/zapret-route-missing-' . getmypid();
    $absentDir = $absentRoot . '/OPNsense/Zapret';
    check(@mkdir($absentDir, 0700, true), 'Cannot create negative routing fixture');
    try {
        foreach (['IndexController', 'DiagnosticsController'] as $name) {
            check(copy($controllers . '/OPNsense/Zapret/' . $name . '.php',
                       $absentDir . '/' . $name . '.php'),
                  'Cannot create missing-Voice baseline');
        }
        putenv('ZAPRET_UI_CONTROLLERS_DIR=' . $absentRoot);
        $missing = false;
        try {
            (new Router('/ui/'))->routeRequest('/ui/zapret/voice', [
                'controller' => 'IndexController',
                'action' => 'indexAction',
            ]);
        } catch (InvalidUriException $e) {
            $missing = true;
        }
        check($missing, 'Router failed to reject the exact _194 missing VoiceController file');
    } finally {
        foreach (['IndexController', 'DiagnosticsController'] as $name) {
            @unlink($absentDir . '/' . $name . '.php');
        }
        @rmdir($absentDir);
        @rmdir($absentRoot . '/OPNsense');
        @rmdir($absentRoot);
    }

    echo "PASS: OPNsense 26.7 Router resolves real menu/controller/action/form/view; missing _194 Voice handler rejected" . PHP_EOL;
}
