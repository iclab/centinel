<?php

if(!isset($_POST["country"]))
{
    echo "Error";
    exit;
}

echo "			Research Consent Form";
echo "Project Title: Characterizing worldwide deployments of Internet censorship technology

Principal Investigator: Prof. Phillipa Gill

Co-Investigators: Prof. Ron Deibert (Faculty, Munk School of Global Affairs, University of Toronto)

Department: Computer Science

You are being asked to be a volunteer in a research study.

PURPOSE:
The purpose of this study is:
To document and analyze the practice";
/*$path = './forms/' . $_POST["country"] . '.txt';
if(file_exists($path)) {
$file = file_get_contents($path, FILE_USE_INCLUDE_PATH);
}
else {
$file = file_get_contents("./forms/Generic.txt", FILE_USE_INCLUDE_PATH);
}
echo($file) */

?>
