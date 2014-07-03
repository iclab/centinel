<?php

if(!isset($_POST["country"]))
{
    echo "Error";
    exit;
}

$path = './forms/' . $_POST["country"] . '.txt';
if(file_exists($path)) {
$file = file_get_contents($path, FILE_USE_INCLUDE_PATH);
}
else {
$file = file_get_contents("./forms/Generic.txt", FILE_USE_INCLUDE_PATH);
}
echo($file)

?>
