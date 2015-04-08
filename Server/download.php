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

if ($fileType == 'baseline') {
    $rootFolder = $baselineFolder . DIRECTORY_SEPARATOR . $projectName;
}
else {
    if (!$projectSubmitTargets[$fileType]['can_download']) {
        header('Content-Type: application/json');

        echo json_encode(array('error' => 'File downloading not allowed!'));
        exit();
    }

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

    if ($projectSubmitTargets[$fileType]['aggregate']) {
        $rootFolder = $dataFolder . DIRECTORY_SEPARATOR . $projectName;

        if (isset($aggregateMap[$projectName])) {
            $aggregatedFolders = $aggregateMap[$projectName];
        }
        else {
            $aggregatedFolders = array();
        }

        $aggregatedFolders[] = $projectName;
    }
    else {
        $rootFolder = $dataFolder . DIRECTORY_SEPARATOR . $projectName . DIRECTORY_SEPARATOR . $clientName . DIRECTORY_SEPARATOR . $sessionId . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'];
    }
}

if (!file_exists($rootFolder)) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid project!'));
    exit();
}

if ($projectSubmitTargets[$fileType]['aggregate']) {
    if (substr_count($_GET['f'], "::") == 2) {
        list($projectBucket, $bucket, $relFilePath) = explode('::', $_GET['f']);
    }
    else{
        list($bucket, $relFilePath) = explode('::', $_GET['f']);
    }

    $bucketFound = false;
    foreach ($aggregatedFolders as $folderName) {
        $clientIterator = new DirectoryIterator($dataFolder . DIRECTORY_SEPARATOR . $folderName);

        if (sha1($folderName) == $projectBucket) {
            foreach($clientIterator as $path => $o) {
                if (!$o->isDot() && $o->isDir()) {
                    $sessionIterator = new DirectoryIterator($dataFolder . DIRECTORY_SEPARATOR . $folderName . DIRECTORY_SEPARATOR . $o->getFileName());
                    foreach($sessionIterator as $path => $os) {
                        if (!$os->isDot() && $os->isDir()) {
                            $folder = $dataFolder . DIRECTORY_SEPARATOR . $folderName . DIRECTORY_SEPARATOR . $o->getFileName() . DIRECTORY_SEPARATOR . $os->getFileName() . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'];

                            if (sha1(str_replace($dataFolder . DIRECTORY_SEPARATOR . $folderName, '', $folder)) == $bucket) {
                                $bucketFound = true;
                                $rootFolder = $dataFolder . DIRECTORY_SEPARATOR . $folderName;
                                break 3;
                            }
                        }
                    }
                }
            }
        }
    }

    if (!$bucketFound) {
        header('Content-Type: application/json');

        echo json_encode(array('error' => 'Invalid bucket!'));
        exit();
    }

    $filePath = realpath($folder . DIRECTORY_SEPARATOR . $relFilePath);
}
else {
    $filePath = realpath($rootFolder . DIRECTORY_SEPARATOR . $_GET['f']);
}

if ($rootFolder != substr($filePath, 0, strlen($rootFolder))) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid file path!'));
    exit();
}

if (!file_exists($filePath)) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'File missing!'));
    exit();
}

header('Content-Description: File Transfer');
header('Content-Type: application/octet-stream');
header('Content-Disposition: attachment; filename='.basename($filePath));
header('Expires: 0');
header('Cache-Control: must-revalidate');
header('Pragma: public');
header('Content-Length: ' . filesize($filePath));
readfile($filePath);
exit;