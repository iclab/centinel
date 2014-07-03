<?php

if(!isset($_POST["country"]))
{
    echo "Error";
    exit;
}

echo $_POST["country"];

?>