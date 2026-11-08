<?php

/**
 * LC-05: one-time initial configuration after the very first plugin install.
 *
 * Store two user-approved values through the normal native model and
 * Config::save(), exactly as a form save would. NEVER synthesize values in
 * a model getter or a page renderer, and never alter an existing Zapret root,
 * including empty previously saved fields and ordinary pkg reinstall.
 */
namespace OPNsense\Zapret\Native;

final class InitialConfig
{
    public const YOUTUBE_DOMAINS = <<<'DOMAINS'
youtube.com
googlevideo.com
yt.be
youtu.be
ytimg.com
youtubei.googleapis.com
youtube.googleapis.com
youtube-nocookie.com
ggpht.com
ssl.gstatic.com
DOMAINS;

    public const TRAFFIC_STRATEGY = <<<'STRATEGY'
--filter-tcp=80,443
--filter-l7=http,tls
<HOSTLIST:youtube>
--blob=http_iana_org
--out-range=-d10
--payload=http_req
--lua-desync=fake:blob=http_iana_org:tcp_md5
--lua-desync=multisplit:pos=method+2
--payload=tls_client_hello
--lua-desync=multisplit:pos=midsld:seqovl=1

--new

--filter-udp=443
--filter-l7=quic
<HOSTLIST:youtube>
--out-range=-d10
--payload=quic_initial
--lua-desync=fake:blob=fake_default_quic:repeats=5
STRATEGY;

    /**
     * Returns 'initialized' or 'preserved'; callers must not create any
     * runtime/FD9/IPFW resource. Config::save() releases the native lock.
     */
    public static function initialize(object $config, callable $modelFactory): string
    {
        $saveAttempted = false;
        $config->lock();
        try {
            // Check the persisted subtree under the real Config lock, not
            // a model field default; checking missing leaves is insufficient.
            $existing = $config->xpath('//OPNsense/Zapret');
            if (!is_object($existing) || !isset($existing->length)) {
                throw new \RuntimeException('Native Zapret Config lookup failed');
            }
            if ($existing->length !== 0) {
                // Any previous configuration wins, even empty field values.
                return 'preserved';
            }

            $model = $modelFactory();
            foreach ([
                'strategy.trafficargs' => self::TRAFFIC_STRATEGY,
                'hostlist.youtubedomains' => self::YOUTUBE_DOMAINS,
            ] as $reference => $value) {
                if ($model->setNodeByReference($reference, $value) !== true) {
                    throw new \RuntimeException('Native first-install model refused field');
                }
            }
            if (count($model->performValidation(false)) !== 0) {
                throw new \RuntimeException('Native first-install model validation failed');
            }
            if ($model->serializeToConfig(false, true) !== true) {
                throw new \RuntimeException('Native first-install Config serialization failed');
            }

            $saveAttempted = true;
            $config->save([
                'description' => 'Initialized clean Zapret2 Traffic Strategy and YouTube Domains',
            ]);
            return 'initialized';
        } catch (\Throwable $error) {
            // A native save may already have persisted. Never retry or
            // overwrite an ambiguous saved state as though it were blank.
            if ($saveAttempted) {
                throw new \RuntimeException(
                    'Native first-install Config save outcome requires review', 0, $error
                );
            }
            throw $error;
        } finally {
            $config->unlock();
        }
    }

    public static function main(): int
    {
        try {
            if (PHP_OS_FAMILY !== 'BSD' || function_exists('posix_geteuid') &&
                posix_geteuid() !== 0) {
                throw new \RuntimeException('Native root OPNsense Config required');
            }
            require_once('script/load_phalcon.php');
            $status = self::initialize(
                \OPNsense\Core\Config::getInstance(),
                static fn() => new \OPNsense\Zapret\Zapret()
            );
            fwrite(STDOUT, "zapret-config=$status\n");
            return 0;
        } catch (\Throwable $error) {
            // No configuration bytes, hostnames or strategy payload in logs.
            fwrite(STDERR, "ERROR: Zapret2 initial native Config unavailable or uncertain\n");
            return 69;
        }
    }
}

if (PHP_SAPI === 'cli' && realpath((string)($argv[0] ?? '')) === __FILE__) {
    exit(InitialConfig::main());
}
