{#
    Copyright (C) 2026 Umur Gorur
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.
#}

<script>
    $(document).ready(function() {
        const data_get_map = {'frm_GeneralSettings': "/api/zapret/settings/get"};
        const isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
        const runtimeText = {
            title: isRussian ? 'Служба Zapret2' : 'Zapret2 Service',
            repositoryReleases: isRussian ? 'Релизы репозитория' : 'Repository Releases',
            started: isRussian ? 'Запущена' : 'Started',
            stopped: isRussian ? 'Остановлена' : 'Stopped',
            error: '{{ lang._("Error") }}',
            start: '{{ lang._("Start") }}',
            stop: '{{ lang._("Stop") }}',
            apply: '{{ lang._("Apply") }}',
            applying: isRussian ? 'Применение…' : 'Applying…',
            loading: isRussian ? 'Загрузка…' : 'Loading…',
            unavailable: isRussian ? 'Недоступно' : 'Unavailable',
            notInstalled: 'not installed',
            operationFailed: isRussian
                ? 'Установка Zapret2 завершилась с ошибкой. Подробности: /var/log/zapret2/setup.log'
                : 'Zapret2 installation failed. See /var/log/zapret2/setup.log for details.',
            setupError: isRussian ? 'Ошибка установки Zapret2' : 'Zapret2 setup error',
            applyError: isRussian ? 'Ошибка применения настроек' : 'Settings Apply failed',
            applyReview: isRussian
                ? 'Результат обновления upstream не подтверждён. Обновите страницу и проверьте версию и службу перед повтором. Подробности: /var/log/zapret2/setup.log'
                : 'Upstream update result is unconfirmed. Reload and inspect the version and service before retrying. See /var/log/zapret2/setup.log.'
        };
        const extrasText = {
            install: isRussian ? 'Установить дополнительные ресурсы' : 'Install Additional Resources',
            remove: isRussian ? 'Удалить дополнительные ресурсы' : 'Remove Additional Resources',
            removePlanTitle: isRussian ? 'План удаления дополнительных ресурсов' : 'Additional Resources removal plan',
            removePlanInfo: isRussian ? 'Будут удалены дополнительные файлы: ' : 'Additional files selected for removal: ',
            removeNotReady: isRussian ? 'Запуск проверочной службы ещё не подключён. Удаление недоступно, файлы и служба не изменены.' :
                'The native trial service Apply is not yet connected. Removal is unavailable; no files or service state were changed.',
            removeNoop: isRussian ? 'Дополнительных файлов для удаления нет.' : 'No additional resources require removal.',
            removePlanError: isRussian ? 'Не удалось получить подтверждённый план удаления. Файлы не изменены.' :
                'Could not obtain the verified removal plan. No files were changed.',
            firstStart: isRussian ? 'Сначала запустите Zapret2' : 'Start Zapret2 first',
            unavailable: isRussian ? 'Состояние ресурсов недоступно' : 'Resource status unavailable',
            notInstalled: isRussian ? 'Дополнительные ресурсы не установлены' : 'Additional Resources not installed',
            downloading: isRussian ? 'Загрузка ресурсов…' : 'Downloading resources…',
            verifying: isRussian ? 'Проверка файлов…' : 'Verifying resources…',
            installing: isRussian ? 'Установка и перезапуск Zapret2…' : 'Installing and restarting Zapret2…',
            recovering: isRussian ? 'Восстановление после ошибки…' : 'Restoring previous resources…',
            failed: isRussian ? 'Не удалось установить ресурсы' : 'Resource installation failed',
            restoreFailed: isRussian ? 'Не удалось восстановить прежнее состояние' : 'Previous state could not be restored',
            review: isRussian ? 'Требуется проверка результата перед повторной попыткой' :
                'Review the previous result before trying again',
            ready: isRussian ? 'Установлено' : 'Installed',
            restored: isRussian ? 'Дополнительные ресурсы восстановлены' : 'Additional Resources restored',
            removing: isRussian ? 'Удаление дополнительных ресурсов…' : 'Removing Additional Resources…',
            lua: 'Lua', bin: 'BIN',
            native: isRussian ? 'Из установленной версии Zapret2' : 'Included in installed Zapret2',
            other: isRussian ? 'Остальные установленные ресурсы' : 'Other installed resources',
            installHelp: isRussian
                ? 'Дополнительные ресурсы пока не установлены. Нажмите «Установить дополнительные ресурсы», чтобы добавить новые .lua и .bin файлы.'
                : 'Additional Resources have not been installed. Click “Install Additional Resources” to add extra .lua and .bin files.',
            listUnavailable: isRussian ? 'Кэш списка ресурсов недоступен. Обновление списка выполняется после установки или смены версии Zapret2.'
                : 'The resource list cache is unavailable. It is updated after installation or a Zapret2 version change.',
            none: isRussian ? 'Нет установленных файлов' : 'No installed files',
            log: '/var/log/zapret2/extra-resources.log'
        };
        let extraPoll = null;
        let extraPollAttempts = 0;
        let helpInventoryLoaded = false;
        let helpInventoryRequest = false;
        let helpInventoryPendingRefresh = false;
        let resourceHelpWasVisible = false;
        let helpInventoryLastInstalled = false;
        let extraStateKnown = false;
        let extraBusy = false;
        let extraInstallPending = false;
        let extraRemovePending = false;
        let extraExpectedOperation = '';
        let extraNeedsReview = false;
        let runtimePoll = null;
        let runtimeWasBusy = false;
        let runtimeStatusInFlight = false;
        let releaseNeedsReview = false;
        let releaseExpectedVersion = '';
        let releaseOriginalVersion = '';
        let releaseOriginalService = '';
        let releaseObservedBusy = false;
        let releaseApplyStartedAt = 0;
        const releaseApplyDeadlineMs = 10 * 60 * 1000;
        let currentServiceState = 'error';
        let currentRuntimeInstalled = false;
        let releaseApplyPending = false;
        let strategiesApplyPending = false;
        let strategiesApplyNeedsReview = false;

        // The Telegram IPSET is also editable on Voice Transmission. Include
        // its original value in the Strategies POST as a concurrency token.
        // A stale browser tab is rejected before the model or runtime changes.
        const telegramBaseline = $('<input/>', {
            type: 'hidden', id: 'zapret.sync.telegramips_baseline'
        });
        $('#frm_GeneralSettings').append(telegramBaseline);

        function reloadSettings() {
            return mapDataToFormUI(data_get_map).done(function() {
                const currentField = document.getElementById('zapret.hostlist.telegramips');
                telegramBaseline.val(currentField ? currentField.value : '');
                formatTokenizersUI();
                $('.selectpicker').selectpicker('refresh');
            });
        }

        // Keep known pre-dispatch errors localized like the rest of the UI.
        // Other PHP exception strings are not suitable as UI translations.
        function localizeStrategiesApplyError(message) {
            if (!isRussian) return message;
            const translations = {
                'Candidate changes fields outside the owning form':
                    'Кандидат изменяет поля, не принадлежащие форме «Стратегии».',
                'Candidate changes a foreign field':
                    'Кандидат изменяет постороннее поле конфигурации.',
                'Shared change map omits candidate field':
                    'В списке изменений отсутствует поле кандидата.',
                'Shared change map includes unchanged field':
                    'В списке изменений указано неизменённое поле.',
                'Strategies candidate field validation refused':
                    'Проверка изменённого поля стратегии не пройдена.',
                'Missing or invalid Strategies baseline; reload this page':
                    'Исходное состояние стратегии не подтверждено. Обновите страницу.',
                'Shared Apply request is too large; shorten the destination lists':
                    'Размер изменённых данных превышает допустимый лимит передачи. Настройки не применены.'
            };
            return translations[message] ||
                'Предварительная проверка настроек не пройдена. Изменения не применены.';
        }
        function showRuntimeError(title, message) {
            BootstrapDialog.show({
                type: BootstrapDialog.TYPE_DANGER,
                title: title,
                message: $('<div/>').text(message),
                buttons: [{
                    label: '{{ lang._("Close") }}',
                    action: function(dialog) { dialog.close(); }
                }]
            });
        }

        function setRuntimeBusy(busy) {
            // Controls must stay locked for both operations, but each Apply
            // button owns only its own spinner.
            const controlsBusy = !!busy || releaseApplyPending || releaseNeedsReview ||
                strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview || extraRemovePending;
            const releaseAvailable = $('#zapretReleaseSelect option').filter(function() {
                return /^v[0-9]+(?:\.[0-9]+)+$/.test(this.value);
            }).length > 0;
            const serviceControllable = currentRuntimeInstalled &&
                (currentServiceState === 'started' || currentServiceState === 'stopped');

            $('#zapretServiceControl').prop('disabled', controlsBusy || !serviceControllable);
            $('#zapretReleaseSelect').prop('disabled', controlsBusy || !releaseAvailable);
            $('#zapretReleaseApply').prop('disabled', controlsBusy || !releaseAvailable);
            // Lower Strategies Apply is a separate action/spinner, but must
            // never compete with an Additional Resources lifecycle transaction.
            $('#reconfigureAct').prop('disabled', controlsBusy);
            $('#zapretReleaseApplyText').text(releaseApplyPending ? runtimeText.applying : runtimeText.apply);
            $('#zapretReleaseApplyProgress').toggleClass('fa fa-spinner fa-pulse', releaseApplyPending);
            const extrasAllowed = currentRuntimeInstalled && currentServiceState === 'started' &&
                extraStateKnown && !controlsBusy;
            $('#zapretExtraInstall').prop('disabled', !extrasAllowed);
            $('#zapretExtraInstall').attr('title', currentServiceState === 'stopped'
                ? extrasText.firstStart : (extraNeedsReview ? extrasText.review : extrasText.install));
            $('#zapretExtraProgress').toggleClass('fa fa-spinner fa-pulse',
                extraBusy || extraInstallPending);
            $('#zapretExtraRemove').prop('disabled', !extrasAllowed || extraRemovePending);
            $('#zapretExtraRemoveProgress').toggleClass('fa fa-spinner fa-pulse', extraRemovePending);
        }

        function reconcileStrategiesApplyControls() {
            $('#reconfigureAct').prop('disabled',
                strategiesApplyPending || strategiesApplyNeedsReview);
            $('#reconfigureActProgress').toggleClass('fa fa-spinner fa-pulse',
                strategiesApplyPending);
            setRuntimeBusy(runtimeWasBusy);
        }

        // The runtime worker can finish between polls, or its status endpoint
        // can transiently fail while native FD9 is held. Correlate the desired
        // release with a real busy observation OR a changed committed version.
        // An unchanged-version replay with no busy evidence remains uncertain.
        function releaseTerminalOutcome(data, target, previous, service, observedBusy) {
            if (!data || data.busy || !data.installed) return 'pending';
            const progressed = observedBusy || (previous !== target && data.version === target);
            if (!progressed) return 'pending';
            if (data.setup === 'failed') return 'failed';
            if (data.setup === 'ready' && data.version === target && data.service === service) {
                return 'success';
            }
            return 'pending';
        }

        function stopRuntimePolling() {
            if (runtimePoll !== null) {
                window.clearInterval(runtimePoll);
                runtimePoll = null;
            }
        }

        function ensureRuntimePolling(busy) {
            if ((releaseApplyPending || busy) && runtimePoll === null) {
                runtimePoll = window.setInterval(refreshRuntime, 2000);
            } else if (!releaseApplyPending && !busy) {
                stopRuntimePolling();
            }
        }

        function finishReleaseOperation(needsReview, failureMessage) {
            releaseApplyPending = false;
            releaseNeedsReview = releaseNeedsReview || !!needsReview;
            releaseExpectedVersion = '';
            releaseOriginalVersion = '';
            releaseOriginalService = '';
            releaseObservedBusy = false;
            releaseApplyStartedAt = 0;
            if (failureMessage) {
                showRuntimeError(runtimeText.setupError, failureMessage);
            }
        }

        function renderRuntime(data) {
            const installed = !!(data && data.installed);
            const service = data && ['started', 'stopped', 'error'].indexOf(data.service) !== -1
                ? data.service
                : 'error';
            const busy = !!(data && data.busy);
            const badge = $('#zapretServiceStatus');
            const serviceButton = $('#zapretServiceControl');
            const wasBusy = runtimeWasBusy;
            let failureReported = false;

            if (releaseApplyPending && (busy || (data && data.setup === 'installing'))) {
                releaseObservedBusy = true;
            }
            if (releaseApplyPending) {
                const outcome = releaseTerminalOutcome(data, releaseExpectedVersion,
                    releaseOriginalVersion, releaseOriginalService, releaseObservedBusy);
                if (outcome === 'success') {
                    finishReleaseOperation(false, '');
                    helpInventoryLoaded = false;
                    requestResourceHelpInventory(true);
                } else if (outcome === 'failed') {
                    failureReported = true;
                    finishReleaseOperation(false, runtimeText.operationFailed);
                }
            }

            currentRuntimeInstalled = installed;
            if (!busy) currentServiceState = installed ? service : 'error';
            badge.removeClass('label-success label-default label-danger label-info');

            if (busy) {
                // The native lifecycle is intentionally STOPPED during an
                // upstream build; do not publish its transient error as a
                // terminal service failure or block on its FD9 status.
                badge.addClass('label-info').text(runtimeText.applying);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.hide().prop('disabled', true);
            } else if (!installed) {
                badge.addClass('label-danger').text(runtimeText.error);
                $('#zapretRuntimeVersion').text(runtimeText.notInstalled);
                serviceButton.hide().prop('disabled', true);
            } else if (service === 'started') {
                badge.addClass('label-success').text(runtimeText.started);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.show().text(runtimeText.stop).prop('disabled', busy);
            } else if (service === 'stopped') {
                badge.addClass('label-default').text(runtimeText.stopped);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.show().text(runtimeText.start).prop('disabled', busy);
            } else {
                badge.addClass('label-danger').text(runtimeText.error);
                $('#zapretRuntimeVersion').text(data.version || '—');
                serviceButton.hide().prop('disabled', true);
            }

            if (wasBusy && !busy && data && data.setup === 'failed' && !failureReported &&
                !releaseApplyPending) {
                showRuntimeError(runtimeText.setupError, runtimeText.operationFailed);
            }
            runtimeWasBusy = busy;
            setRuntimeBusy(busy);
            ensureRuntimePolling(busy);
        }

        function renderRuntimeRequestFailure() {
            if (releaseApplyPending || runtimeWasBusy) {
                // Transient API failures are not evidence that native setup
                // failed. Preserve the last valid view and continue polling.
                ensureRuntimePolling(runtimeWasBusy);
                setRuntimeBusy(runtimeWasBusy);
                return;
            }
            currentRuntimeInstalled = false;
            currentServiceState = 'error';
            $('#zapretServiceStatus')
                .removeClass('label-success label-default label-danger label-info')
                .addClass('label-danger')
                .text(runtimeText.error);
            $('#zapretRuntimeVersion').text('—');
            $('#zapretServiceControl').hide().prop('disabled', true);
            setRuntimeBusy(false);
        }

        function refreshRuntime() {
            if (releaseApplyPending && releaseApplyStartedAt &&
                Date.now() - releaseApplyStartedAt >= releaseApplyDeadlineMs) {
                finishReleaseOperation(true, runtimeText.applyReview);
                ensureRuntimePolling(runtimeWasBusy);
                setRuntimeBusy(runtimeWasBusy);
            }
            // Never stack multiple 30s status requests while setup.lock/FD9
            // is held: one request in flight is sufficient.
            if (runtimeStatusInFlight) return;
            runtimeStatusInFlight = true;
            return $.ajax({
                type: 'POST',
                url: '/api/zapret/service/runtime',
                dataType: 'json',
                timeout: 30000
            }).done(renderRuntime).fail(renderRuntimeRequestFailure).always(function() {
                runtimeStatusInFlight = false;
            });
        }

        function refreshReleases(selectedVersion) {
            const select = $('#zapretReleaseSelect');
            select.prop('disabled', true).empty().append(
                $('<option/>').attr('value', '').text(runtimeText.loading)
            );

            return $.ajax({
                type: 'POST',
                url: '/api/zapret/service/releases',
                dataType: 'json',
                timeout: 60000
            }).done(function(data) {
                select.empty();
                if (!data || data.status !== 'ok' || !Array.isArray(data.releases)) {
                    select.append($('<option/>').attr('value', '').text(runtimeText.unavailable));
                    setRuntimeBusy(runtimeWasBusy);
                    return;
                }

                data.releases.forEach(function(release) {
                    select.append($('<option/>').attr('value', release).text(release));
                });
                if (selectedVersion && select.find('option[value="' + selectedVersion + '"]').length) {
                    select.val(selectedVersion);
                }
                setRuntimeBusy(runtimeWasBusy);
            }).fail(function() {
                select.empty().append($('<option/>').attr('value', '').text(runtimeText.unavailable));
                setRuntimeBusy(runtimeWasBusy);
            });
        }

        function isResourceAdvancedEnabled() {
            return $('#show_advanced_frm_GeneralSettings').hasClass('fa-toggle-on');
        }

        function updateResourceAdvancedVisibility() {
            $('#zapretExtraRemoveRow').toggle(isResourceAdvancedEnabled());
        }

        // This is the native OPNsense Advanced toggle, independent of Help.
        const resourceAdvancedIcon = document.getElementById('show_advanced_frm_GeneralSettings');
        if (resourceAdvancedIcon && window.MutationObserver) {
            const observer = new MutationObserver(updateResourceAdvancedVisibility);
            observer.observe(resourceAdvancedIcon, {attributes: true, attributeFilter: ['class']});
        }
        updateResourceAdvancedVisibility();

        function isResourceHelpEnabled() {
            // Native OPNsense 26.7 full-help toggle for frm_GeneralSettings.
            return $('#show_all_help_frm_GeneralSettings').hasClass('fa-toggle-on');
        }

        function renderResourceHelpInventory(data) {
            const panel = $('#zapretExtraResourceHelp');
            panel.empty();
            if (!data || data.status !== 'ok') {
                // A missing/corrupt cache is UNKNOWN, never evidence of absence.
                panel.append($('<p/>').text(extrasText.listUnavailable));
                return;
            }
            helpInventoryLastInstalled = !!data.installed;
            if (!data.installed) {
                panel.append($('<p/>').text(extrasText.installHelp));
                return;
            }
            const legend = $('<div/>', {'class': 'zapret-resource-legend'});
            $('<span/>', {'class': 'text-success'}).text(extrasText.native).appendTo(legend);
            $('<span/>', {'class': 'text-info'}).text(extrasText.other).appendTo(legend);
            panel.append(legend);
            const columns = $('<div/>', {'class': 'zapret-resource-columns'});
            [['lua', extrasText.lua], ['bin', extrasText.bin]].forEach(function(pair) {
                const name = pair[0];
                const items = Array.isArray(data[name]) ? data[name] : [];
                const column = $('<div/>', {'class': 'zapret-resource-column'});
                $('<strong/>').text(pair[1] + ' (' + items.length + ')').appendTo(column);
                const list = $('<ul/>', {'class': 'list-unstyled zapret-resource-list'});
                items.forEach(function(item) {
                    if (!item || typeof item.name !== 'string' ||
                        !/^[A-Za-z0-9_.+\-]+\.(lua|bin)$/.test(item.name)) return;
                    $('<li/>').addClass(item.origin === 'upstream' ? 'text-success' : 'text-info')
                        .text(item.name).appendTo(list);
                });
                if (!list.children().length) {
                    $('<li/>', {'class': 'text-muted'}).text(extrasText.none).appendTo(list);
                }
                column.append(list);
                columns.append(column);
            });
            panel.append(columns);
        }

        function requestResourceHelpInventory(force) {
            if (!isResourceHelpEnabled()) return;
            if (helpInventoryRequest) {
                helpInventoryPendingRefresh = helpInventoryPendingRefresh || !!force;
                return;
            }
            if (helpInventoryLoaded && !force) return;
            helpInventoryRequest = true;
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesInventory',
                dataType: 'json',
                timeout: 10000
            }).done(function(data) {
                helpInventoryLoaded = !!data && data.status === 'ok';
                if (isResourceHelpEnabled()) renderResourceHelpInventory(data);
            }).fail(function() {
                if (isResourceHelpEnabled()) renderResourceHelpInventory(null);
            }).always(function() {
                helpInventoryRequest = false;
                if (helpInventoryPendingRefresh) {
                    helpInventoryPendingRefresh = false;
                    requestResourceHelpInventory(true);
                }
            });
        }

        function updateResourceHelpVisibility() {
            const enabled = isResourceHelpEnabled();
            const panel = $('#zapretExtraResourceHelp');
            panel.toggle(enabled);
            // Every new help opening reads the cheap CACHE again, not Git.
            if (enabled && !resourceHelpWasVisible) {
                panel.text(extrasText.loading);
                requestResourceHelpInventory(true);
            }
            resourceHelpWasVisible = enabled;
        }

        // Observe the same icon controlled by OPNsense's full-help switch,
        // including keyboard shortcuts; do not introduce a second help toggle.
        const resourceHelpIcon = document.getElementById('show_all_help_frm_GeneralSettings');
        if (resourceHelpIcon && window.MutationObserver) {
            const observer = new MutationObserver(updateResourceHelpVisibility);
            observer.observe(resourceHelpIcon, {attributes: true, attributeFilter: ['class']});
        }
        updateResourceHelpVisibility();

        function extrasLabel(data) {
            const phase = data && data.phase || 'unknown';
            const installed = data && data.installed;
            const detail = data && typeof data.detail === 'string' ? data.detail : '';

            // Active transactions and unsafe recovery must never be
            // represented as a completed installation or absence.
            switch (phase) {
                case 'downloading': return extrasText.downloading;
                case 'verifying': return extrasText.verifying;
                case 'installing': return extrasText.installing;
                case 'recovering': return extrasText.recovering;
                case 'removing': return extrasText.removing;
                case 'restore_failed': return extrasText.restoreFailed + ' · ' + extrasText.log;
                case 'recovery_required': return extrasText.review + ' · ' + extrasText.log;
                case 'failed':
                    // R1 deliberate Remove failure AFTER verified native rollback.
                    // Other installation failures retain their real error label.
                    if (installed === true && /^REMOVE_FAILED_RESTORED:/.test(detail)) {
                        return extrasText.restored;
                    }
                    return extrasText.failed + ' · ' + extrasText.log;
            }

            // The same validated inventory cache drives full Help and this
            // summary. An unknown cache is NOT "not installed".
            if (installed !== true && installed !== false) return extrasText.unavailable;
            if (phase === 'not_installed' && installed) {
                return extrasText.review + ' · ' + extrasText.log;
            }
            if (!installed) return extrasText.notInstalled;
            if (phase === 'restored') return extrasText.restored;
            if (phase === 'ready') {
                const revision = /^[a-f0-9]{40}$/.test(data.revision || '') ?
                    ' · ' + data.revision.slice(0, 12) : '';
                return extrasText.ready + ': Lua ' + (data.lua || 0) +
                    ', BIN ' + (data.bin || 0) + revision;
            }
            if (phase === 'no_recovery_needed') return extrasText.ready;
            // Unknown/foreign receipt: do not advertise Ready by inference.
            return extrasText.unavailable;
        }

        function stopExtrasPolling() {
            if (extraPoll !== null) {
                window.clearInterval(extraPoll);
                extraPoll = null;
            }
            extraPollAttempts = 0;
        }

        // A fast operation may finish without a polled busy=1 transition.
        // Match the persisted terminal receipt to this exact user click.
        function extraOperationTerminal(data, operation) {
            return !!operation && !!data && data.operation === operation &&
                !data.busy && ['ready', 'failed', 'restore_failed',
                    'recovery_required'].indexOf(data.phase) !== -1;
        }

        function renderExtras(data) {
            if (!data || data.status !== 'ok') {
                extraStateKnown = false;
                extraNeedsReview = true;
                extraBusy = false;
                $('#zapretExtraState').text(extrasText.unavailable);
                stopExtrasPolling();
                setRuntimeBusy(runtimeWasBusy);
                return;
            }

            extraStateKnown = true;
            extraBusy = !!data.busy;
            if (typeof data.installed === 'boolean') {
                if (helpInventoryLoaded && helpInventoryLastInstalled !== data.installed) {
                    // A cache-backed install/removal boundary changed while
                    // Help is open. Re-read the same cache, never scan Git.
                    helpInventoryLoaded = false;
                    requestResourceHelpInventory(true);
                }
                helpInventoryLastInstalled = data.installed;
            }
            if (['restore_failed', 'recovery_required'].indexOf(data.phase) >= 0) {
                extraNeedsReview = true;
            }
            $('#zapretExtraState').text(extrasLabel(data));
            if (extraInstallPending && extraOperationTerminal(data, extraExpectedOperation)) {
                helpInventoryLoaded = false;
                requestResourceHelpInventory(true);
                extraInstallPending = false;
                extraExpectedOperation = '';
                if (data.phase !== 'ready') {
                    extraNeedsReview = true;
                }
                refreshRuntime();
            }
            if (extraInstallPending || extraBusy) {
                if (extraPoll === null) {
                    extraPollAttempts = 0;
                    extraPoll = window.setInterval(refreshExtrasStatus, 2000);
                }
            } else {
                stopExtrasPolling();
            }
            setRuntimeBusy(runtimeWasBusy);
        }

        function refreshExtrasStatus() {
            if (++extraPollAttempts > 300) {
                extraNeedsReview = true;
                extraInstallPending = false;
                extraBusy = false;
                stopExtrasPolling();
                $('#zapretExtraState').text(extrasText.review + ' · ' + extrasText.log);
                setRuntimeBusy(runtimeWasBusy);
                return;
            }
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesStatus',
                dataType: 'json',
                timeout: 15000
            }).done(renderExtras).fail(function() {
                extraStateKnown = false;
                extraNeedsReview = true;
                extraBusy = false;
                stopExtrasPolling();
                $('#zapretExtraState').text(extrasText.unavailable);
                setRuntimeBusy(runtimeWasBusy);
            });
        }

        $('#zapretServiceTitle').text(runtimeText.title);
        $('#zapretRepositoryReleasesLabel').text(runtimeText.repositoryReleases);

        $('#zapretServiceControl').off('click').on('click', function(event) {
            event.preventDefault();
            if (strategiesApplyPending || strategiesApplyNeedsReview || runtimeWasBusy ||
                extraBusy || extraInstallPending || extraNeedsReview ||
                (currentServiceState !== 'started' && currentServiceState !== 'stopped')) {
                return;
            }

            const button = $(this);
            const action = currentServiceState === 'started' ? 'stop' : 'start';
            button.prop('disabled', true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/' + action,
                dataType: 'json',
                timeout: 600000
            }).done(function() {
                refreshRuntime();
                updateServiceControlUI('zapret');
            }).fail(function() {
                refreshRuntime();
            });
        });

        $('#zapretReleaseApply').off('click').on('click', function(event) {
            event.preventDefault();
            const version = $('#zapretReleaseSelect').val();
            if (!version || runtimeWasBusy || releaseApplyPending ||
                strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview) {
                return;
            }

            if (!currentRuntimeInstalled ||
                (currentServiceState !== 'started' && currentServiceState !== 'stopped') ||
                releaseNeedsReview) return;
            releaseApplyPending = true;
            releaseExpectedVersion = version;
            releaseOriginalVersion = $('#zapretRuntimeVersion').text();
            releaseOriginalService = currentServiceState;
            releaseObservedBusy = false;
            releaseApplyStartedAt = Date.now();
            setRuntimeBusy(true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/install',
                data: {'version': version},
                dataType: 'json',
                timeout: 30000
            }).done(function(data) {
                // Start polling independently of whether the first status
                // response actually catches busy=1.
                ensureRuntimePolling(false);
                refreshRuntime();
                refreshReleases(data && data.version ? data.version : version);
            }).fail(function() {
                // A transport timeout may happen after dispatch. Never
                // silently unlock a potentially live second transaction.
                finishReleaseOperation(true, runtimeText.applyReview);
                ensureRuntimePolling(false);
                setRuntimeBusy(runtimeWasBusy);
                refreshRuntime();
            });
        });

        $('#zapretExtraInstallText').text(extrasText.install);
        $('#zapretExtraRemoveText').text(extrasText.remove);
        // Match the existing Install button's rendered dimensions; no new
        // bespoke CSS button size or alternative OPNsense styling.
        $('#zapretExtraRemove').css({
            width: $('#zapretExtraInstall').outerWidth() + 'px',
            height: $('#zapretExtraInstall').outerHeight() + 'px'
        });
        updateResourceAdvancedVisibility();
        $('#zapretExtraRemove').off('click').on('click', function(event) {
            event.preventDefault();
            if (!isResourceAdvancedEnabled() || !extraStateKnown ||
                extraBusy || extraInstallPending || extraRemovePending || extraNeedsReview ||
                runtimeWasBusy || releaseApplyPending || strategiesApplyPending ||
                strategiesApplyNeedsReview || currentServiceState !== 'started') return;
            extraRemovePending = true;
            setRuntimeBusy(runtimeWasBusy);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesRemovePlan',
                dataType: 'json',
                timeout: 130000
            }).done(function(data) {
                if (!data || data.status !== 'ok' ||
                    !Number.isInteger(data.lua) || !Number.isInteger(data.bin) ||
                    data.lua < 0 || data.bin < 0 || data.total !== data.lua + data.bin ||
                    !/^[a-f0-9]{64}$/.test(data.inventory_sha256 || '') ||
                    data.ready !== false) {
                    showRuntimeError(extrasText.removePlanTitle, extrasText.removePlanError);
                    return;
                }
                const summary = data.total === 0 ? extrasText.removeNoop :
                    extrasText.removePlanInfo + 'Lua: ' + data.lua + ', BIN: ' + data.bin + '.';
                BootstrapDialog.show({
                    type: BootstrapDialog.TYPE_INFO,
                    title: extrasText.removePlanTitle,
                    message: $('<div/>').text(summary + '\n' + extrasText.removeNotReady),
                    buttons: [{
                        label: '{{ lang._("Close") }}',
                        action: function(dialog) { dialog.close(); }
                    }]
                });
            }).fail(function() {
                showRuntimeError(extrasText.removePlanTitle, extrasText.removePlanError);
            }).always(function() {
                extraRemovePending = false;
                setRuntimeBusy(runtimeWasBusy);
            });
        });
        $('#zapretExtraState').text(extrasText.notInstalled);
        $('#zapretExtraInstall').off('click').on('click', function(event) {
            event.preventDefault();
            if (!extraStateKnown || extraBusy || extraInstallPending || extraNeedsReview ||
                runtimeWasBusy || releaseApplyPending || strategiesApplyPending ||
                strategiesApplyNeedsReview || currentServiceState !== 'started') {
                return;
            }
            extraInstallPending = true;
            extraExpectedOperation = '';
            setRuntimeBusy(true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/resourcesInstall',
                dataType: 'json',
                timeout: 30000
            }).done(function(data) {
                if (!data || data.status !== 'ok' || !data.started ||
                    !/^[a-f0-9]{32}$/.test(data.operation || '')) {
                    extraNeedsReview = true;
                    extraInstallPending = false;
                    $('#zapretExtraState').text(extrasText.failed);
                } else {
                    extraExpectedOperation = data.operation;
                }
                refreshExtrasStatus();
            }).fail(function() {
                extraInstallPending = false;
                extraExpectedOperation = '';
                extraNeedsReview = true;
                $('#zapretExtraState').text(extrasText.failed + ' · ' + extrasText.log);
                refreshRuntime();
            });
        });

        reloadSettings();
        refreshRuntime();
        refreshReleases();
        refreshExtrasStatus();

        // One original-FD9 Apply, same result handling as Voice. A network
        // timeout is not proof that native Config/runtime/IPFW were untouched.
        $("#reconfigureAct").off('click').on('click', function(event) {
            event.preventDefault();
            if (strategiesApplyPending || strategiesApplyNeedsReview ||
                extraBusy || extraInstallPending || extraNeedsReview || runtimeWasBusy ||
                releaseApplyPending) return;
            strategiesApplyPending = true;
            reconcileStrategiesApplyControls();

            function finishApply() {
                strategiesApplyPending = false;
                reconcileStrategiesApplyControls();
                updateServiceControlUI('zapret');
                refreshRuntime();
            }
            function needsReview() {
                strategiesApplyNeedsReview = true;
                showRuntimeError(runtimeText.applyError, runtimeText.applyReview);
            }

            $.ajax({
                type: 'POST',
                url: '/api/zapret/settings/apply',
                data: getFormData('frm_GeneralSettings'),
                dataType: 'json',
                // Native configdpRun may run for 600s. A short default
                // timeout must not invite another Apply during that worker.
                timeout: 630000
            }).done(function(data) {
                handleFormValidation('frm_GeneralSettings',
                    (data && data.validations) || {});
                if (data && data.result === 'saved' && data.status === 'ok') {
                    reloadSettings().done(function() {
                        if (data.normalized && Array.isArray(data.normalization)) {
                            BootstrapDialog.show({
                                type: BootstrapDialog.TYPE_INFO,
                                title: '{{ lang._("Settings normalized") }}',
                                message: $('<div/>').text(data.normalization.join('\n'))
                                    .css('white-space', 'pre-line'),
                                buttons: [{
                                    label: '{{ lang._("Close") }}',
                                    action: function(dialog) { dialog.close(); }
                                }]
                            });
                        }
                    }).fail(function() {
                        // Applied, but our original Telegram baseline could
                        // not be refreshed. Do not retry from a stale form.
                        needsReview();
                    }).always(finishApply);
                } else {
                    if (!data || data.result !== 'failed' ||
                        data.requires_review === true) {
                        needsReview();
                    } else if (typeof data.message === 'string' && data.message) {
                        // Only explicitly rejected, pre-dispatch errors are
                        // editable without a new Config snapshot.
                        showRuntimeError(runtimeText.applyError,
                            localizeStrategiesApplyError(data.message));
                    }
                    finishApply();
                }
            }).fail(function() {
                needsReview();
                finishApply();
            });
        });

        updateServiceControlUI('zapret');
    });
</script>

<style>
    #zapretExtraResourceHelp { padding: 12px 4px 4px; }
    .zapret-resource-legend { display: flex; flex-wrap: wrap; gap: 6px 24px; margin-bottom: 12px; }
    .zapret-resource-columns { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; }
    .zapret-resource-column { min-width: 0; }
    .zapret-resource-list { max-height: 360px; overflow-y: auto; margin-top: 8px; }
    .zapret-resource-list li { overflow-wrap: anywhere; line-height: 1.6; }
    @media (max-width: 700px) {
        .zapret-resource-columns { grid-template-columns: minmax(0, 1fr); }
    }
    #zapretServiceLine {
        display: grid;
        grid-template-columns: max-content max-content 14ch 12ch 4ch max-content minmax(130px, 150px) max-content;
        align-items: center;
        column-gap: 8px;
        min-height: 34px;
        min-width: max-content;
        white-space: nowrap;
    }

    #zapretRuntimeVersion {
        display: inline-block;
        width: 14ch;
    }

    #zapretServiceControlSlot {
        display: inline-block;
        width: 12ch;
    }

    #zapretServiceControl {
        min-width: 12ch;
    }

    #zapretServiceLine .zapret-service-spacer {
        display: inline-block;
        width: 4ch;
    }

    #zapretReleaseSelect {
        width: 150px;
        min-width: 130px;
    }
</style>

<div class="content-box __mb">
    {{ partial("layout_partials/base_form",['fields':generalForm,'id':'frm_GeneralSettings']) }}

    <div class="table-responsive">
        <table class="table table-striped table-condensed" style="table-layout: fixed; width: 100%; margin-bottom: 0;">
            <colgroup>
                <col style="width: 25%;" />
                <col style="width: 40%;" />
                <col style="width: 35%;" />
            </colgroup>
            <thead id="zapretServiceHeader" style="cursor: pointer;">
                <tr>
                    <th colspan="3">
                        <div style="padding-bottom: 5px; padding-top: 5px; font-size: 16px;">
                            <i id="zapretServiceCollapseIcon" class="fa fa-angle-down" aria-hidden="true"></i>
                            &nbsp;
                            <b id="zapretServiceTitle">Zapret2 Service</b>
                        </div>
                    </th>
                </tr>
            </thead>
            <tbody id="zapretServiceBody" class="collapsible">
                <tr>
                    <td colspan="3">
                        <div id="zapretServiceLine">
                            <b>{{ lang._("Status") }}:</b>
                            <span id="zapretServiceStatus" class="label label-danger">{{ lang._("Error") }}</span>
                            <strong id="zapretRuntimeVersion">not installed</strong>
                            <span id="zapretServiceControlSlot">
                                <button class="btn btn-default" id="zapretServiceControl" type="button" disabled style="display: none;">
                                    {{ lang._("Start") }}
                                </button>
                            </span>
                            <span class="zapret-service-spacer" aria-hidden="true"></span>
                            <label id="zapretRepositoryReleasesLabel" for="zapretReleaseSelect" style="margin-bottom: 0;">
                                Repository Releases
                            </label>
                            <select class="form-control" id="zapretReleaseSelect" disabled>
                                <option value="">Loading…</option>
                            </select>
                            <button class="btn btn-primary" id="zapretReleaseApply" type="button" disabled>
                                <span id="zapretReleaseApplyText">{{ lang._("Apply") }}</span>
                                <i id="zapretReleaseApplyProgress"></i>
                            </button>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td colspan="3">
                        <div id="zapretExtraResourcesLine" style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                            <button class="btn btn-default" id="zapretExtraInstall" type="button" disabled>
                                <span id="zapretExtraInstallText">Install Additional Resources</span>
                                <i id="zapretExtraProgress"></i>
                            </button>
                            <span id="zapretExtraState" role="status" aria-live="polite"></span>
                        </div>
                        <div id="zapretExtraRemoveRow" style="display:none; margin-top:8px;">
                            <button class="btn btn-default text-info" id="zapretExtraRemove" type="button" disabled>
                                <span id="zapretExtraRemoveText">Remove Additional Resources</span>
                                <i id="zapretExtraRemoveProgress"></i>
                            </button>
                        </div>
                        <div id="zapretExtraResourceHelp" style="display:none;" aria-live="polite"></div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
<section class="grid-bottom-reserve __mt">
    <div class="alert content-box" style="display: flex; align-items: center; margin-bottom: 0;">
        <button
            class="btn btn-primary __mr"
            id="reconfigureAct"
            type="button">
            {{ lang._("Apply") }} <i id="reconfigureActProgress"></i>
        </button>
    </div>
</section>
