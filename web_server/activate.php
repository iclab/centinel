<?php

error_reporting(E_ALL);
// check if all parameters are present and ready.
if(!isset($_POST["email"]) || !isset($_POST["name"]) || !isset($_POST["client_tag"]) || !isset($_POST["country"]))
{
    echo "The information is incomplete.";
    exit;
}

// create MySQL database connection
$db_connection = mysqli_connect("localhost", "centinel_db_user", "C3nt1n3l.2014", "centinel_schema");

// test the connection for errors
if (mysqli_connect_errno()) {
  echo "Failed to connect to MySQL: " . mysqli_connect_error();
  exit;
}

$qresult = mysqli_query($db_connection, "SELECT * FROM centinel_schema.clients WHERE clients.client_tag=\"" . $_POST["client_tag"] . "\"");
if(!$qresult)
{
  echo "Failed to execute MySQL query: " . mysqli_connect_error();
  exit;
}

$found = 0;
while($row = mysqli_fetch_array($qresult))
{
    $found = 1;
    if($row['authorized'] != "0")
    {
	echo "Error: client already active (or activation email already sent).";
	exit;
    }
}
/*
if($found == "0")
{
    echo "Error: client tag not valid.";
    exit;
}
*/

$activation_token = rand(100000, 999999);
$to = $_POST["email"];
$subject = "ICLab-Centinel Client Activation";
$body = "Hello,\n
We have recently received a request to activate a measurement device with your email (id: " . $_POST["client_tag"] .")\n.
Please make sure that this information is correct by checking your device (the id tag is on the side of your device).\n
If you have confirmed that this is your device, click on the link below to activate:\n\n
http://130.245.145.2:8080/activate.php?token=" . $activation_token . "&client_tag=" . $_POST["client_tag"] . "\n\n
If you did not send this request, we are sorry for the inconvenience.\n
We encourage you to report this incident by emailing us at info@iclab.org\n
\n
Thank you,\n
The ICLab Team";

$headers = "From: " . "do-not-reply@iclab.org" . "\r\n" . "X-Mailer: php";

if (mail($to, $subject, $body, $headers))
{
    echo("Activation email sent. Check your email.");
    mysqli_query($db_connection, "UPDATE clients SET authorized=" . $activation_token . 
		" name=\'". $_POST["name"] . 
		"\' email=\'" . $_POST["email"] . 
		"\' country=1 WHERE client_tag=\'" . $_POST["client_tag"] . "\'");
}
else
{
    $error = error_get_last();
    echo("Error: message delivery failed..." .  $error["message"]);
}

mysqli_close($db_connection);

?>