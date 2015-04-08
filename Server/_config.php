<?php

// A list with the project names that are available to download and accept incoming sync requests.
$currentProjects = array(
    'example',
);

// Use this to merge the queue of "another-project" in the queue of "example". 
// This can for example be usefull to have a small group of fuzzers working with a different version of the binary to 
$aggregateMap = array(
    //'example' => array('another-project'),
);

// Do we allow new clients to join? (And get a session token)
$acceptNewSessionIds = true;

// Where to find the baseline data (the project that is downloaded to the client)
$baselineFolder = __DIR__ . '/baseline';

// Where should the data be stored.
$dataFolder = __DIR__ . '/data';

// Path to this script
$baseUrl = 'https://www.example.com/api/v1';

// Most likely you dont want to touch this (or the client is also modified for it)
$projectSubmitTargets = array(
    'session' => array(
        'folder' => 'sessions',
        'can_download' => false,
        'aggregate' => false,
        'allow_overwrite' => true,
        'allow_duplicates' => true,
    ),

    'queue' => array(
        'folder' => 'queue',
        'can_download' => true,
        'aggregate' => true,
        'allow_overwrite' => false,
        'allow_duplicates' => false,
    ),
    'hang' => array(
        'folder' => 'hangs',
        'can_download' => false,
        'aggregate' => false,
        'allow_overwrite' => false,
        'allow_duplicates' => false,
    ),
    'crash' => array(
        'folder' => 'crashes',
        'can_download' => false,
        'aggregate' => false,
        'allow_overwrite' => false,
        'allow_duplicates' => false,
    )
);