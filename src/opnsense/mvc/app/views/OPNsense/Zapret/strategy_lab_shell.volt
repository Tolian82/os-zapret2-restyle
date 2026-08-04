{#
    Dormant Strategy Lab Patch 2 GUI shell.

    This partial is packaged but intentionally not included by diagnostics.volt until
    the final asynchronous migration patch. It establishes the approved polling,
    progress, bilingual cancellation, and Stop test contracts without changing the
    current Blockcheck Run-button behavior.
#}
<script>
    $(document).ready(function() {
        const isRussian = ((document.documentElement.lang || '').toLowerCase().indexOf('ru') === 0);
        const strategyLabMessages = isRussian
            ? {
                stop: 'Прервать тест',
                canceled: 'SKIPPED — отменено',
                requestFailed: 'Не удалось получить состояние Strategy Lab.'
            }
            : {
                stop: 'Stop test',
                canceled: 'SKIPPED — canseled',
                requestFailed: 'Strategy Lab status request failed.'
            };
        let strategyLabJobId = '';
        let strategyLabPollTimer = null;

        function strategyLabSetPolling(enabled) {
            if (strategyLabPollTimer !== null) {
                window.clearInterval(strategyLabPollTimer);
                strategyLabPollTimer = null;
            }
            if (enabled && strategyLabJobId) {
                strategyLabPollTimer = window.setInterval(function() {
                    strategyLabStatus(strategyLabJobId);
                }, 1000);
            }
        }

        function strategyLabRender(data) {
            const shell = $("#strategyLabShell");
            const summary = $("#strategyLabProgress");
            const stages = $("#strategyLabStages").empty();

            if (!data || data.status === 'error') {
                summary.text((data && data.message) || strategyLabMessages.requestFailed);
                strategyLabSetPolling(false);
                return;
            }

            shell.show();
            strategyLabJobId = data.job_id || strategyLabJobId;
            summary.text(data.message || ((data.state || data.status || '').toUpperCase()));

            (data.stages || []).forEach(function(stage) {
                $('<div/>')
                    .text(stage.number + ' ' + stage.status + (stage.message ? ' — ' + stage.message : ''))
                    .appendTo(stages);
            });

            if (data.state === 'completed' || data.state === 'error') {
                strategyLabSetPolling(false);
                $("#strategyLabStopBtn").prop('disabled', true);
            }
        }

        function strategyLabStatus(jobId) {
            $.ajax({
                type: 'POST',
                url: '/api/zapret/strategylab/status',
                data: {'job_id': jobId || ''},
                dataType: 'json',
                timeout: 10000,
                success: strategyLabRender,
                error: function() {
                    strategyLabRender({status: 'error', message: strategyLabMessages.requestFailed});
                }
            });
        }

        function strategyLabStart(target, mode) {
            $.ajax({
                type: 'POST',
                url: '/api/zapret/strategylab/start',
                data: {
                    'target': target,
                    'mode': mode || 'standard',
                    'language': isRussian ? 'ru' : 'en'
                },
                dataType: 'json',
                timeout: 10000,
                success: function(data) {
                    strategyLabRender(data);
                    if (data && data.status === 'ok' && data.job_id) {
                        strategyLabJobId = data.job_id;
                        $("#strategyLabStopBtn").prop('disabled', false);
                        strategyLabSetPolling(true);
                    }
                },
                error: function() {
                    strategyLabRender({status: 'error', message: strategyLabMessages.requestFailed});
                }
            });
        }

        function strategyLabCancel() {
            if (!strategyLabJobId) {
                return;
            }
            $("#strategyLabStopBtn").prop('disabled', true);
            $.ajax({
                type: 'POST',
                url: '/api/zapret/strategylab/cancel',
                data: {'job_id': strategyLabJobId},
                dataType: 'json',
                timeout: 10000,
                success: strategyLabRender,
                error: function() {
                    strategyLabRender({status: 'error', message: strategyLabMessages.requestFailed});
                }
            });
        }

        function strategyLabDiscover() {
            $.ajax({
                type: 'POST',
                url: '/api/zapret/strategylab/status',
                data: {'job_id': ''},
                dataType: 'json',
                timeout: 10000,
                success: function(data) {
                    if (data && data.status !== 'idle') {
                        strategyLabRender(data);
                        if (data.job_id && data.state !== 'completed' && data.state !== 'error') {
                            strategyLabJobId = data.job_id;
                            $("#strategyLabStopBtn").prop('disabled', false);
                            strategyLabSetPolling(true);
                        }
                    }
                }
            });
        }

        $("#strategyLabStopBtn")
            .text(strategyLabMessages.stop)
            .click(strategyLabCancel);

        window.strategyLabShell = {
            start: strategyLabStart,
            status: strategyLabStatus,
            cancel: strategyLabCancel,
            canceledMessage: strategyLabMessages.canceled
        };
        strategyLabDiscover();
    });
</script>

<div id="strategyLabShell" style="display: none;">
    <div id="strategyLabProgress"></div>
    <div id="strategyLabStages"></div>
    <button class="btn btn-default" id="strategyLabStopBtn" type="button"></button>
</div>
