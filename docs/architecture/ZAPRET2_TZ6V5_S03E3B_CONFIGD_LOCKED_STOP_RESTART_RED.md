# ТЗ_6v5 S03e3b — реальный Stop/Restart отказ на original FD9 BUSY

**23.11.2026. Исходный кандидат v0.6.5_140, основание: merged main 0e877e99, PR #1250.**

Цель: воспроизвести старые физические ошибки Stop/Restart на disposable OPNsense 26.7 через штатный configd и shell **без** возможности остановить или запустить службу. Отдельно исследовать, какие ошибки получают API и GUI, не считать HTTP 200 доказательством Stop/Restart.

Сначала read-only подтверждаются чистый установленный plugin, отсутствие upstream dvtws2/supervisor, отсутствие pending pkg-update/постороннего FD9 и Config/IPFW snapshot. Только на одноразовой VM реальный оригинальный FD9 удерживается тестовым lockf; независимый contender доказывает BUSY перед вызовами. Под ним `zapret_service.sh stop|restart` должен вернуть реальный rc75, а `configctl zapret stop|restart` — наблюдаемую нативную форму ответа. Config/IPFW/процессы должны остаться идентичны, никакого перехода service_dispatch быть не может. Пока не закрыт возможный асинхронный configd child, FD9 не освобождать.

У upstream OPNsense `ApiMutableServiceControllerBase::{stop,restart}Action()` возвращается только `['response'=>$response]` от Backend::configdRun; `general.volt` после `.done()` без проверки terminal receipt делает refresh. Это RED риска ложного успеха, а не основание менять runtime без изолированного native evidence. Локализация реального backend Stop/Restart в RU/EN остаётся открытой.

**Статус PENDING exact-head CI.** S03e3b пока NO-GO; полный S03 NO-GO; S04–S20 не начинать. Действующая OPNsense и пользовательские .pkg не затрагиваются. Запрещены независимый Config writer, SIGSTOP/SIGCONT, чужие IPFW, физический Stop в этой проверке.

Связанные: [ТЗ](TZ_6v5.md), [план](ZAPRET2_TZ6V5_STEP_BY_STEP_PLAN.md), [Issue #1225](https://github.com/Tolian82/os-zapret2-restyle/issues/1225), [S03e3a](ZAPRET2_TZ6V5_S03E3_NATIVE_WAN_START_USEREXCEPTION_RUEN.md).
