<?php
echo "<option selected disabled hidden value=\" \"></option>";
echo "<option value=\"Other\">Other</option>";
$path = "./forms/country_list.txt";
$file = file_get_contents($path, FILE_USE_INCLUDE_PATH);
$lines = explode("\n", $file);
foreach ($lines as $country) 
{
  //  echo "<option value=\"Other\">Other</option>";
echo '<option value="' . $country . '">' . $country . '</option>';
}

?>

