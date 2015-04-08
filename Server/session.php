<?php

require '_config.php';
require '_func.php';

if (!$acceptNewSessionIds) {
    http_response_code(403);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'New sessionIds are not available!'));
    exit();
}

if (($projectName = request_project_name()) === false) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid project!'));
    exit();
}

if (!isset($_GET['c']) || empty($_GET['c']) || preg_match('/^([a-zA-Z0-9-]+\.)*[a-zA-Z0-9]+$/', $_GET['c']) < 1) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid client name!'));
    exit();
}

$clientName = $_GET['c'];

if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName)) {
    if (!mkdir($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName)) {
        header('Content-Type: application/json');

        echo json_encode(array('error' => 'Can\'t add client!'));
        exit();
    }
}

// If a session token is give, we update the session
if (isset($_GET['s'])) {
    if (!isset($_GET['s']) || empty($_GET['s']) || preg_match('/^[a-zA-Z0-9]+$/', $_GET['s']) < 1) {
        header('Content-Type: application/json');

        echo json_encode(array('error' => 'Invalid session token!'));
        exit();
    }

    $sessionId = $_GET['s'];

    if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId)) {
        header('Content-Type: application/json');

        echo json_encode(array('error' => 'Invalid session token!'));
        exit();
    }
}
else {
    $sessionId = sha1(uniqid($_SERVER['REMOTE_ADDR'], true));

    if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId)) {
        if (!mkdir($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId)) {
            header('Content-Type: application/json');

            echo json_encode(array('error' => 'Can\'t add client!'));
            exit();
        }
    }

    foreach ($projectSubmitTargets as $targetName => $targetInfo) {
        if (!mkdir($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId . DIRECTORY_SEPARATOR . $targetInfo['folder'])) {
            header('Content-Type: application/json');

            echo json_encode(array('error' => 'Can\'t add client!'));
            exit();
        }
    }
}

$sessionInfo = array(
    'project_name' => $projectName,
    'client_name' => $clientName,
    'session_id' => $sessionId,
    'session_update_url' => $baseUrl . DIRECTORY_SEPARATOR . 'session.php?c='.$clientName.'&p='.$projectName . '&s=' . $sessionId,
    'files_url' => $baseUrl . DIRECTORY_SEPARATOR . 'files.php?c='.$clientName.'&p='.$projectName . '&s=' . $sessionId
);

foreach ($projectSubmitTargets as $targetName => $targetInfo) {
    if ($targetInfo['can_download']) {
        $sessionInfo[$targetName . '_download_url'] = $baseUrl . DIRECTORY_SEPARATOR . 'files.php?c='.$clientName.'&p='.$projectName.'&t=' . $targetName . '&s=' . $sessionId;
    }

    $sessionInfo[$targetName . '_submit_url'] = $baseUrl . DIRECTORY_SEPARATOR . 'submit.php?c='.$clientName.'&p='.$projectName.'&t=' . $targetName . '&s=' . $sessionId;
}

header('Content-Type: application/json');

echo json_encode($sessionInfo);