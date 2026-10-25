/*
 * FreeBSD 15 disposable-jail-only marker: genuine dynamically linked ELF.
 * NOT real dvtws2 or Lua and NEVER launched directly from the host.
 * The STATIC boundary probe must establish kernel jail/no-IP boundary
 * before execve("/loader-marker", ...).
 */
#if !defined(__FreeBSD__)
#error "FreeBSD CI-only dynamic-loader marker"
#endif

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    int jailed = 0;
    size_t length = sizeof(jailed);
    struct stat st;

    if (sysctlbyname("security.jail.jailed", &jailed, &length, NULL, 0) != 0 ||
        length != sizeof(jailed) || jailed != 1) {
        fputs("DYNAMIC_MARKER_NOT_JAILED\n", stderr);
        return 31;
    }
    if (stat("/conf/config.xml", &st) == 0 ||
        stat("/usr/local/etc/zapret2", &st) == 0 ||
        stat("/host-only-secret", &st) == 0) {
        fputs("DYNAMIC_MARKER_HOST_PATH_VISIBLE\n", stderr);
        return 32;
    }
    puts("JAIL_REAL_DYNAMIC_LOADER_SYNTHETIC_ELF_PASS");
    return 0;
}
