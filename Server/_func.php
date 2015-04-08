<?php

function request_project_name() {
    global $currentProjects;

    if (!isset($_GET['p']) || !in_array($_GET['p'], $currentProjects)) {
        return false;
    }

    return $_GET['p'];
}

function request_filetype() {
    global $projectSubmitTargets;

    if (!isset($_GET['t']) || empty($_GET['t']) || !array_key_exists($_GET['t'], $projectSubmitTargets)) {
        return 'baseline';
    }

    return $_GET['t'];
}