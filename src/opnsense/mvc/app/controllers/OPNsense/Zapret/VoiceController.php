<?php

/**
 * UI entry for the existing Voice Transmission form.
 * The OPNsense /ui/zapret/voice URL resolves to VoiceController::indexAction.
 * Mutations continue to use the separate shared Voice API/Strategies backend.
 */
namespace OPNsense\Zapret;

use OPNsense\Base\IndexController as BaseIndexController;

class VoiceController extends BaseIndexController
{
    public function indexAction()
    {
        $this->view->pick('OPNsense/Zapret/voice');
        $this->view->voiceForm = $this->getForm('voice');
    }
}
