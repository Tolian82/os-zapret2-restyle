/*
 * FreeBSD 15 native-kernel TEST-ONLY boundary proof. Compiled STATIC,
 * executed inside an ephemeral jail with a private empty root filesystem.
 * Never executes zapret2/dvtws2 or loads real Lua.
 */
#if !defined(__FreeBSD__)
#error "FreeBSD jail proof only"
#endif
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int no_file(const char *path)
{
    struct stat st;
    errno = 0;
    if (stat(path, &st) == 0)
        return 0;
    return errno == ENOENT || errno == ENOTDIR;
}
static int cannot_bind_ip(void)
{
    struct sockaddr_in addr;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
        return 1; /* Kernel refused even the address family. */
    memset(&addr, 0, sizeof(addr));
    addr.sin_len = sizeof(addr);
    addr.sin_family = AF_INET;
    addr.sin_port = htons(0);
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    int rc = bind(fd, (const struct sockaddr *)&addr, sizeof(addr));
    close(fd);
    return rc == -1;
}
int main(int argc, char **argv)
{
    if ((argc != 2 && !(argc == 3 &&
        (strcmp(argv[2], "--exec-mock") == 0 ||
         strcmp(argv[2], "--exec-loader-test") == 0 ||
         strcmp(argv[2], "--exec-ci-upstream-positive") == 0 ||
         strcmp(argv[2], "--exec-ci-upstream-missing-export") == 0 ||
         strcmp(argv[2], "--exec-ci-upstream-missing-lua") == 0))) ||
        !argv[1] || !argv[1][0]) {
        fprintf(stderr, "HOST_CANARY_ARGUMENT_REQUIRED\n");
        return 10;
    }
    int jailed = 0;
    size_t size = sizeof(jailed);
    if (sysctlbyname("security.jail.jailed", &jailed, &size, NULL, 0) ||
        size != sizeof(jailed) || jailed != 1) {
        fprintf(stderr, "NOT_A_JAIL\n");
        return 11;
    }
    if (!no_file("/conf/config.xml") ||
        !no_file("/usr/local/etc/zapret2") ||
        !no_file(argv[1])) {
        fprintf(stderr, "HOST_PATH_VISIBLE\n");
        return 12;
    }
    int raw = socket(PF_DIVERT, SOCK_RAW, 0);
    if (raw != -1) {
        close(raw);
        fprintf(stderr, "DIVERT_SOCKET_ALLOWED\n");
        return 13;
    }
    raw = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (raw != -1) {
        close(raw);
        fprintf(stderr, "RAW_IPV4_ALLOWED\n");
        return 14;
    }
    raw = socket(AF_INET6, SOCK_RAW, IPPROTO_RAW);
    if (raw != -1) {
        close(raw);
        fprintf(stderr, "RAW_IPV6_ALLOWED\n");
        return 15;
    }
    if (!cannot_bind_ip()) {
        fprintf(stderr, "JAIL_IPV4_LOOPBACK_BIND_SUCCEEDED\n");
        return 16;
    }
    int local = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (local == -1) {
        fprintf(stderr, "LOCAL_AF_UNIX_UNAVAILABLE\n");
        return 17;
    }
    close(local);
    puts("JAIL_PRIVATE_ROOT_NO_IP_NO_RAW_SOCKET_PASS");
    if (argc == 3) {
        /*
         * CI-only bridge: kernel checks must succeed BEFORE preload exists.
         * The static jail probe runs without LD_PRELOAD, then execs the
         * synthetic dynamic mock with an explicit jail-relative library.
         * Neither the host's jexec nor this probe loads the interposer.
         */
        if (strcmp(argv[2], "--exec-mock") == 0) {
            char *const args[] = { "/mock-engine", NULL };
            char *const env[] = { "LD_PRELOAD=/no-net.so", "PATH=/", NULL };
            fflush(stdout);
            execve("/mock-engine", args, env);
            perror("JAILED_MOCK_EXEC_FAILED");
            return 18;
        }
        /*
         * CI ONLY: exec genuine *CI-built upstream v1.0.6* FreeBSD dvtws2,
         * never an appliance-installed binary. Identical static KERNEL
         * boundary checked above BEFORE this dispatch and any LD_PRELOAD.
         * The interposer is NOT security isolation; the jail is.
         */
        if (strncmp(argv[2], "--exec-ci-upstream-", 19) == 0) {
            const int missing_export =
                strcmp(argv[2], "--exec-ci-upstream-missing-export") == 0;
            const int missing_lua =
                strcmp(argv[2], "--exec-ci-upstream-missing-lua") == 0;
            char *const args[] = {
                "/ci-engine", "--intercept=0", "--uid=65534:65534", "--debug=1",
                "--filter-tcp=443",
                missing_lua ? "--lua-init=@/upstream/lua/missing.lua"
                            : "--lua-init=@/upstream/lua/zapret-lib.lua",
                missing_export ? "--lua-desync=__ci_export_absent__"
                               : "--lua-desync=pass",
                "--new", "--filter-udp=443", "--lua-desync=pass",
                NULL
            };
            char *const env[] = {
                "PATH=/", "LD_PRELOAD=/no-net.so",
                "LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/lib", NULL
            };
            fflush(stdout);
            execve("/ci-engine", args, env);
            perror("JAILED_UPSTREAM_CI_ENGINE_EXEC_FAILED");
            return 20;
        }
        /* No shim or untrusted environment: actual FreeBSD ld-elf.so.1
         * starts only a CI-built synthetic marker inside the private jail.
         * The KERNEL boundary above must pass before reaching execve. */
        if (strcmp(argv[2], "--exec-loader-test") == 0) {
            char *const args[] = { "/loader-marker", NULL };
            char *const env[] = { "PATH=/", NULL };
            fflush(stdout);
            execve("/loader-marker", args, env);
            perror("JAILED_LOADER_EXEC_FAILED");
            return 19;
        }
    }
    return 0;
}
