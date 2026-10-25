/*
 * Offline-only fake "engine preinit" contract used to verify socket-shim
 * behaviour in FreeBSD CI. NEVER invokes installed dvtws2, Lua or IPFW.
 */
#if !defined(__FreeBSD__)
#error "FreeBSD only"
#endif
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>

static int check_local_divert(int family, int proto)
{
    struct sockaddr_storage peer;
    socklen_t len = sizeof(peer);
    int sock = socket(family, SOCK_RAW, proto);
    int sndbuf = 32768;
    if (sock < 0)
        return 1;
    if (getsockname(sock, (struct sockaddr *)&peer, &len) < 0 ||
        peer.ss_family != AF_UNIX)
        return 2;
    if (setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf)) < 0)
        return 3;
    if (sendto(sock, "NO", 2, 0, NULL, 0) != -1 || errno != EPERM)
        return 4;
    close(sock);
    return 0;
}

int main(void)
{
    int result = check_local_divert(PF_DIVERT, 0);
    if (result) {
        fprintf(stderr, "divert shim failed step %d\n", result);
        return 1;
    }
    result = check_local_divert(AF_INET, IPPROTO_DIVERT);
    if (result) {
        fprintf(stderr, "legacy divert shim failed step %d\n", result);
        return 2;
    }
    if (socket(AF_INET, SOCK_STREAM, 0) != -1 || errno != EPERM)
        return 3;
    if (socket(AF_INET6, SOCK_DGRAM, 0) != -1 || errno != EPERM)
        return 4;
    puts("MOCK_LUA_INIT_REACHED_NO_NETWORK_SOCKET");
    return 0;
}
