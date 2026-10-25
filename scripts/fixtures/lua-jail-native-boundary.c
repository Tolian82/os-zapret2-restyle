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
    if (argc != 2 || !argv[1] || !argv[1][0]) {
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
    return 0;
}
