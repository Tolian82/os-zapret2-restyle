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
            started: '{{ lang._("Started") }}',
            stopped: '{{ lang._("Stopped") }}',
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
            setupError: isRussian ? 'Ошибка установки Zapret2' : 'Zapret2 setup error'
        };
        let runtimePoll = null;
        let runtimeWasBusy = false;
        let currentServiceState = 'error';
        let currentRuntimeInstalled = false;

        function reloadSettings() {
            return mapDataToFormUI(data_get_map).done(function() {
                formatTokenizersUI();
                $('.selectpicker').selectpicker('refresh');
            });
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
            const releaseAvailable = $('#zapretReleaseSelect option').filter(function() {
                return /^v[0-9]+(?:\.[0-9]+)+$/.test(this.value);
            }).length > 0;
            const serviceControllable = currentRuntimeInstalled &&
                (currentServiceState === 'started' || currentServiceState === 'stopped');

            $('#zapretServiceControl').prop('disabled', busy || !serviceControllable);
            $('#zapretReleaseSelect').prop('disabled', busy || !releaseAvailable);
            $('#zapretReleaseApply').prop('disabled', busy || !releaseAvailable);
            $('#zapretReleaseApplyText').text(busy ? runtimeText.applying : runtimeText.apply);
            $('#zapretReleaseApplyProgress').toggleClass('fa fa-spinner fa-pulse', busy);
        }

        function renderRuntime(data) {
            const installed = !!(data && data.installed);
            const service = data && ['started', 'stopped', 'error'].indexOf(data.service) !== -1
                ? data.service
                : 'error';
            const busy = !!(data && data.busy);
            const badge = $('#zapretServiceStatus');
            const serviceButton = $('#zapretServiceControl');

            currentRuntimeInstalled = installed;
            currentServiceState = installed ? service : 'error';
            badge.removeClass('label-success label-default label-danger');

            if (!installed) {
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

            setRuntimeBusy(busy);

            if (runtimeWasBusy && !busy && data && data.setup === 'failed') {
                showRuntimeError(runtimeText.setupError, runtimeText.operationFailed);
            }
            runtimeWasBusy = busy;

            if (busy && runtimePoll === null) {
                runtimePoll = window.setInterval(refreshRuntime, 2000);
            } else if (!busy && runtimePoll !== null) {
                window.clearInterval(runtimePoll);
                runtimePoll = null;
            }
        }

        function renderRuntimeRequestFailure() {
            currentRuntimeInstalled = false;
            currentServiceState = 'error';
            $('#zapretServiceStatus')
                .removeClass('label-success label-default label-danger')
                .addClass('label-danger')
                .text(runtimeText.error);
            $('#zapretRuntimeVersion').text('—');
            $('#zapretServiceControl').hide().prop('disabled', true);
            setRuntimeBusy(runtimeWasBusy);
        }

        function refreshRuntime() {
            return $.ajax({
                type: 'POST',
                url: '/api/zapret/service/runtime',
                dataType: 'json',
                timeout: 30000
            }).done(renderRuntime).fail(renderRuntimeRequestFailure);
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

        $('#zapretServiceTitle').text(runtimeText.title);
        $('#zapretRepositoryReleasesLabel').text(runtimeText.repositoryReleases);

        $('#zapretServiceControl').off('click').on('click', function(event) {
            event.preventDefault();
            if (currentServiceState !== 'started' && currentServiceState !== 'stopped') {
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
            if (!version || runtimeWasBusy) {
                return;
            }

            setRuntimeBusy(true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/service/install',
                data: {'version': version},
                dataType: 'json',
                timeout: 30000
            }).done(function(data) {
                runtimeWasBusy = true;
                refreshRuntime();
                refreshReleases(data && data.version ? data.version : version);
            }).fail(function() {
                setRuntimeBusy(false);
                refreshRuntime();
            });
        });

        reloadSettings();
        refreshRuntime();
        refreshReleases();

        $("#reconfigureAct").off('click').on('click', function(event) {
            event.preventDefault();
            const button = $(this);
            button.prop('disabled', true);

            saveFormToEndpoint(
                "/api/zapret/settings/apply",
                'frm_GeneralSettings',
                function(data) {
                    reloadSettings().always(function() {
                        updateServiceControlUI('zapret');
                        refreshRuntime();
                        button.prop('disabled', false);
                    });

                    if (data && data.normalized && Array.isArray(data.normalization)) {
                        BootstrapDialog.show({
                            type: BootstrapDialog.TYPE_INFO,
                            title: '{{ lang._("Settings normalized") }}',
                            message: $('<div/>').text(data.normalization.join('\n')).css('white-space', 'pre-line'),
                            buttons: [{
                                label: '{{ lang._("Close") }}',
                                action: function(dialog) { dialog.close(); }
                            }]
                        });
                    }
                },
                true,
                function() {
                    button.prop('disabled', false);
                    updateServiceControlUI('zapret');
                    refreshRuntime();
                }
            );
        });

        updateServiceControlUI('zapret');
    });
</script>

<style>
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
            {{ lang._("Apply") }}
        </button>
    </div>
</section>
