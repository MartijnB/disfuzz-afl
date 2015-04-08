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
    $downloadUrlAccessToken = '';
    $rootFolder = $baselineFolder . DIRECTORY_SEPARATOR . $projectName;
}
else {
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

    $downloadUrlAccessToken = '&c='.$clientName.'&s='.$sessionId;

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

if (!file_exists($dataFolder . DIRECTORY_SEPARATOR . $projectName)) {
    http_response_code(500);

    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid project!'));
    exit();
}

$files = array();
$versionHash = sha1('');

if ($fileType != 'baseline' && $projectSubmitTargets[$fileType]['aggregate']) {
    foreach ($aggregatedFolders as $folderName) {
        $clientIterator = new DirectoryIterator($dataFolder . DIRECTORY_SEPARATOR . $folderName);

        foreach($clientIterator as $path => $o) {
            if (!$o->isDot() && $o->isDir()) {
                $sessionIterator = new DirectoryIterator($dataFolder . DIRECTORY_SEPARATOR . $folderName . DIRECTORY_SEPARATOR . $o->getFileName());
                foreach($sessionIterator as $path => $os) {
                    if (!$os->isDot() && $os->isDir()) {
                        $folder = $dataFolder . DIRECTORY_SEPARATOR . $folderName . DIRECTORY_SEPARATOR . $o->getFileName() . DIRECTORY_SEPARATOR . $os->getFileName() . DIRECTORY_SEPARATOR . $projectSubmitTargets[$fileType]['folder'];

                        if (file_exists($folder) && is_dir($folder)) {
                            $fileIterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($folder, FilesystemIterator::SKIP_DOTS));

                            foreach($fileIterator as $path => $o) {
                                $md5Hash = md5_file($path);
                                $sha1Hash = sha1_file($path);

                                $files[] = array(
                                    'path' => str_replace($folder, '', $path),
                                    'size' => filesize($path),
                                    'url' => $baseUrl . DIRECTORY_SEPARATOR . 'download.php?p='.$projectName . $downloadUrlAccessToken .'&t='.$fileType.'&f=' . urlencode(sha1($folderName) . '::'. sha1(str_replace($dataFolder . DIRECTORY_SEPARATOR . $folderName, '', $folder)) . '::'.str_replace($folder, '', $path)),
                                    'md5sum' => $md5Hash,
                                    'sha1sum' => $sha1Hash
                                );

                                $versionHash = sha1($versionHash . str_replace($dataFolder . DIRECTORY_SEPARATOR . $folderName, '', $path) . ':' . filesize($path) . ':' . $sha1Hash);
                            }
                        }
                    }
                }
            }
        }
    }
}
else {
    if (!file_exists($rootFolder)) {
        http_response_code(500);

        header('Content-Type: application/json');

        echo json_encode(array('error' => 'Invalid project!'));
        exit();
    }

    $fileIterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($rootFolder, FilesystemIterator::SKIP_DOTS));

    foreach($fileIterator as $path => $o) {
        $md5Hash = md5_file($path);
        $sha1Hash = sha1_file($path);

        $files[] = array(
            'path' => str_replace($rootFolder, '', $path),
            'size' => filesize($path),
            'url' => $baseUrl . DIRECTORY_SEPARATOR . 'download.php?p='.$projectName . $downloadUrlAccessToken .'&t='.$fileType.'&f=' . urlencode(str_replace($rootFolder, '', $path)),
            'md5sum' => md5_file($path),
            'sha1sum' => sha1_file($path)
        );

        $versionHash = sha1($versionHash . str_replace($rootFolder, '', $path) . ':' . filesize($path) . ':' . $sha1Hash);
    }
}

header('Content-Type: application/json');

echo json_encode(array('files' => $files, 'version' => $versionHash));