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
    $( document ).ready(function() {
        const data_get_map = {'frm_GeneralSettings': "/api/zapret/settings/get"};

        function reloadSettings() {
            return mapDataToFormUI(data_get_map).done(function() {
                formatTokenizersUI();
                $('.selectpicker').selectpicker('refresh');
            });
        }

        reloadSettings();

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
                }
            );
        });

        updateServiceControlUI('zapret');
    });
</script>

<div class="content-box __mb">
    {{ partial("layout_partials/base_form",['fields':generalForm,'id':'frm_GeneralSettings']) }}
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
