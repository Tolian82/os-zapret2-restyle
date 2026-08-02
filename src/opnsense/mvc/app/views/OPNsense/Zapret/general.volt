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
            operationFailed: isRussian
                ? 'Установка Zapret2 завершилась с ошибкой. Подробности: /var/log/zapret2/setup.log'
                : 'Zapret2 installation failed. See /var/log/zapret2/setup.log for details.',
            requestFailed: isRussian ? 'Операция не выполнена.' : 'The operation could not be completed.',
            setupError: isRussian ? 'Ошибка установки Zapret2' : 'Zapret2 setup error'
        };
        let runtimePoll = null;
        let runtimeWasBusy = false;
        let currentServiceState = 'error';

        function reloadSettings() {
            return mapDataToFormUI(data_get_map).done(function() {
                formatTokenizersUI();
                $('.selectpicker').selectpicker('refresh');
            });
        }

        function apiErrorMessage(xhr) {
            if (xhr && xhr.responseJSON) {
                return xhr.responseJSON.message || xhr.responseJSON.error || runtimeText.requestFailed;
            }
            return runtimeText.requestFailed;
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

            $('#zapretServiceControl').prop('disabled', busy || currentServiceState === 'error');
            $('#zapretReleaseSelect').prop('disabled', busy || !releaseAvailable);
            $('#zapretReleaseApply').prop('disabled', busy || !releaseAvailable);
            $('#zapretReleaseApplyText').text(busy ? runtimeText.applying : runtimeText.apply);
            $('#zapretReleaseApplyProgress').toggleClass('fa fa-spinner fa-pulse', busy);
        }

        function renderRuntime(data) {
            const service = data && ['started', 'stopped', 'error'].indexOf(data.service) !== -1
                ? data.service
                : 'error';
            const busy = !!(data && data.busy);
            const badge = $('#zapretServiceStatus');
            const serviceButton = $('#zapretServiceControl');

            currentServiceState = service;
            badge.removeClass('label-success label-default label-danger');
            if (service === 'started') {
                badge.addClass('label-success').text(runtimeText.started);
                serviceButton.text(runtimeText.stop).prop('disabled', busy);
            } else if (service === 'stopped') {
                badge.addClass('label-default').text(runtimeText.stopped);
                serviceButton.text(runtimeText.start).prop('disabled', busy);
            } else {
                badge.addClass('label-danger').text(runtimeText.error);
                serviceButton.text(runtimeText.start).prop('disabled', true);
            }

            $('#zapretRuntimeVersion').text(data && data.version ? data.version : '—');
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
            currentServiceState = 'error';
            $('#zapretServiceStatus')
                .removeClass('label-success label-default label-danger')
                .addClass('label-danger')
                .text(runtimeText.error);
            $('#zapretServiceControl').text(runtimeText.start).prop('disabled', true);
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
            }).fail(function(xhr) {
                select.empty().append($('<option/>').attr('value', '').text(runtimeText.unavailable));
                setRuntimeBusy(runtimeWasBusy);
                showRuntimeError(runtimeText.setupError, apiErrorMessage(xhr));
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
            }).done(function(data) {
                if (!data || data.status !== 'ok') {
                    showRuntimeError(runtimeText.error, runtimeText.requestFailed);
                }
                refreshRuntime();
                updateServiceControlUI('zapret');
            }).fail(function(xhr) {
                showRuntimeError(runtimeText.error, apiErrorMessage(xhr));
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
            }).fail(function(xhr) {
                setRuntimeBusy(false);
                showRuntimeError(runtimeText.setupError, apiErrorMessage(xhr));
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
        display: flex;
        align-items: center;
        flex-wrap: nowrap;
        gap: 8px;
        min-height: 34px;
        white-space: nowrap;
    }

    #zapretServiceLine .zapret-service-spacer {
        width: 28px;
        flex: 0 0 28px;
    }

    #zapretReleaseSelect {
        width: auto;
        min-width: 130px;
    }

    @media (max-width: 900px) {
        #zapretServiceLine {
            flex-wrap: wrap;
            white-space: normal;
        }

        #zapretServiceLine .zapret-service-spacer {
            display: none;
        }
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
                            <strong id="zapretRuntimeVersion">—</strong>
                            <button class="btn btn-default" id="zapretServiceControl" type="button" disabled>
                                {{ lang._("Start") }}
                            </button>
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
