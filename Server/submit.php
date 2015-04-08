<?php

require '_config.php';
require '_func.php';

if (($projectName = request_project_name()) === false) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid project!'));
    exit();
}

$fileType = request_filetype();

if (!isset($_GET['c']) || empty($_GET['c']) || preg_match('/^([a-zA-Z0-9-]+\.)*[a-zA-Z0-9]+$/', $_GET['c']) < 1) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid client name!'));
    exit();
}

$clientName = $_GET['c'];

if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName)) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid client name!'));
    exit();
}

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

$rootFolder = $dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'];

if (!file_exists($rootFolder)) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid project!'));
    exit();
}

if (count($_FILES) === 0) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'File(s) missing!'));
    exit();
}

if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta')) {
    mkdir($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta');
}

if (!$projectSubmitTargets[$fileType]['allow_duplicates']) {
    if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta' . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'].'.dedup')) {
        file_put_contents($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta' . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'].'.dedup', serialize(array()));
    }

    $dedupData = unserialize(file_get_contents($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta' . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'].'.dedup'));
}

$amountFiles = 0;
foreach ($_FILES as $formFileName => $formFileInfo) {
    if ($formFileInfo['error'] == UPLOAD_ERR_OK) {
        if (strpos($formFileInfo['name'], '..') !== false || strpos($formFileInfo['name'], '/') !== false) {
            header('Content-Type: application/json');

            echo json_encode(array('error' => 'Invalid filename!'));
            exit();
        }

        $md5Hash = md5_file($formFileInfo['tmp_name']);

        if (!$projectSubmitTargets[$fileType]['allow_duplicates']) {
            if (array_key_exists($md5Hash, $dedupData)) {
                // A file with this hash already exists
                continue;
            }
        }

        $filePath = $rootFolder . DIRECTORY_SEPARATOR . $formFileInfo['name'];

        if ($rootFolder != substr($filePath, 0, strlen($rootFolder))) {
            header('Content-Type: application/json');

            echo json_encode(array('error' => 'Invalid path!'));
            exit();
        }

        if (file_exists($filePath) && !$projectSubmitTargets[$fileType]['allow_overwrite']) {
            if (md5_file($filePath) != $md5Hash) {
                $i = 1;
                do {
                    $tmpFilePath = dirname($filePath) . DIRECTORY_SEPARATOR . basename($filePath) . ':'.$i;
                    $i++;
                }
                while (file_exists($tmpFilePath));

                $filePath = $tmpFilePath;
            }
        }

        move_uploaded_file($formFileInfo['tmp_name'], $filePath);

        if (!$projectSubmitTargets[$fileType]['allow_duplicates']) {
            $dedupData[$md5Hash] = array(
                'file' => str_replace($rootFolder, '', $filePath)
            );
        }

        $amountFiles++;
    }
}

if (!$projectSubmitTargets[$fileType]['allow_duplicates']) {
    file_put_contents($dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . '.meta' . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'].'.dedup', serialize($dedupData));
}

header('Content-Type: application/json');

echo json_encode(array('error' => $amountFiles . ' file(s) uploaded.'));
exit();