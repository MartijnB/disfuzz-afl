<?php

require '_config.php';
require '_func.php';

if (!isset($_GET['c']) || empty($_GET['c']) || preg_match('/^([a-zA-Z0-9-]+\.)*[a-zA-Z0-9]+$/', $_GET['c']) < 1) {
    header('Content-Type: application/json');

    echo json_encode(array('error' => 'Invalid client name!'));
    exit();
}

$clientName = $_GET['c'];

$projectsInfo = array();

foreach ($currentProjects as $projectName) {
    $projectsInfo[$projectName] = array(
        'name' => $projectName,
        'setup_url' => $baseUrl . DIRECTORY_SEPARATOR . 'session.php?c='.$clientName.'&p='.$projectName
    );
}

header('Content-Type: application/json');

echo json_encode($projectsInfo);