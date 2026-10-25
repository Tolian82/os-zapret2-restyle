/*
 * EXPERIMENTAL TEST-ONLY FreeBSD preloader for testing no-network engine
 * initialization. NOT a security boundary and NOT shipped in an OPNsense pkg.
 *
 * Upstream zapret2 v1.0.6: rawsend_preinit opens PF_DIVERT SOCK_RAW, falling
 * back to AF_INET SOCK_RAW IPPROTO_DIVERT, before lua_init(). An isolated test
 * process can use harmless unconnected AF_UNIX datagram FDs instead.
 *
 * SECURITY: This interposer is insufficient to sandbox any process. Never use
 * it on the live router, never run dvtws2 with it without a separately
 * verified jail with ip4=disable, ip6=disable and private filesystem.
 * No code is authorized to treat shim success as a removal preflight PASS.
 */
#if !defined(__FreeBSD__)
#error "The no-network test shim is strictly FreeBSD-only"
#endif
#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <dlfcn.h>
#include <errno.h>
#include <stddef.h>

typedef int (*socket_call)(int, int, int);
typedef int (*connect_call)(int, const struct sockaddr *, socklen_t);
typedef int (*bind_call)(int, const struct sockaddr *, socklen_t);

static socket_call original_socket(void)
{
    return (socket_call)dlsym(RTLD_NEXT, "socket");
}
static int deny(void)
{
    errno = EPERM;
    return -1;
}
int socket(int domain, int type, int protocol)
{
    socket_call real = original_socket();
    if (!real)
        return deny();

    /* The exact FreeBSD v1.0.6 rawsend_preinit divert probes only. */
    if (type == SOCK_RAW &&
        ((domain == PF_DIVERT && protocol == 0) ||
         (domain == AF_INET && protocol == IPPROTO_DIVERT)))
        return real(AF_UNIX, SOCK_DGRAM, 0);

    /* Do not open any IP socket from the test process, even TCP/UDP. */
    if (domain == AF_INET || domain == AF_INET6 || domain == PF_DIVERT)
        return deny();
    return real(domain, type, protocol);
}
int connect(int fd, const struct sockaddr *to, socklen_t length)
{
    connect_call real = (connect_call)dlsym(RTLD_NEXT, "connect");
    if (!real)
        return deny();
    if (to && (to->sa_family == AF_INET || to->sa_family == AF_INET6 ||
               to->sa_family == PF_DIVERT))
        return deny();
    return real(fd, to, length);
}
int bind(int fd, const struct sockaddr *to, socklen_t length)
{
    bind_call real = (bind_call)dlsym(RTLD_NEXT, "bind");
    if (!real)
        return deny();
    if (to && (to->sa_family == AF_INET || to->sa_family == AF_INET6 ||
               to->sa_family == PF_DIVERT))
        return deny();
    return real(fd, to, length);
}
ssize_t sendto(int fd, const void *buf, size_t n, int flags,
               const struct sockaddr *to, socklen_t len)
{
    (void)fd; (void)buf; (void)n; (void)flags; (void)to; (void)len;
    /* Never transmit packets, including via unconnected divert stand-ins. */
    errno = EPERM;
    return -1;
}
