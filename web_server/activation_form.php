<?php

echo "<html>\n<head>\n";
echo "<title>\n";
echo "ICLab Test Unit Activation Form";
echo "</title>\n";
echo "<link rel=\"stylesheet\" type=\"text/css\" href=\"css/general_style.css\" />\n";
echo "</head>\n";
echo "<body onload=\"javascript:load_countries()\">";
echo "<div id=\"mom\">\n
<div id=\"headtitle\">
ICLab<br/>
</div>\n";
echo "\n</div>\n";
echo
"<div id=\"maincontainer\" style=\"center top no-repeat\">\n
<div id=\"content-left\" align=\"justify\">\n
";
echo
'<br/>
<script type="text/javascript">
if (window.XMLHttpRequest)
{   // code for IE7+, Firefox, Chrome, Opera, Safari
    xmlhttp=new XMLHttpRequest();
    xmlhttpconsent=new XMLHttpRequest();
    xmlhttpcountries=new XMLHttpRequest();
}
else
{	// code for IE6, IE5
    xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    xmlhttpconsent=new ActiveXObject("Microsoft.XMLHTTP");
    xmlhttpcountries=new ActiveXObject("Microsoft.XMLHTTP");
}
function validemail(email) {
 
   var reg = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
   var address = document.getElementById(email).value;
   if(reg.test(address) == false) {
      return false;
   }
   return true;
}

function show_consent_form()
{
    var dropdown = document.getElementById("countrydropdown");
    country = dropdown.options[dropdown.selectedIndex].text;
    xmlhttpconsent.onreadystatechange=function()
    {
        if (xmlhttpconsent.readyState==4 && xmlhttpconsent.status==200)
    	{
    	    if(xmlhttpconsent.responseText == "Error")
    	    {
		alert("Country error!");
		return;
    	    }
    	    document.getElementById("consent_form_text").innerHTML = xmlhttpconsent.responseText;
	}
    }

    getstr = "consent_form.php";
    args = "country=" + encodeURIComponent(country);
    
    xmlhttpconsent.open("POST",getstr,true);
    xmlhttpconsent.setRequestHeader("Content-type", "application/x-www-form-urlencoded")
    xmlhttpconsent.send(args);
}

function load_countries() 
{
    alert("Loaded");
    var dropdown = document.getElementById("countrydropdown");
    xmlhttpcountries.onreadystatechange=function()
    {
        if (xmlhttpcountries.readyState==4 && xmlhttpcountries.status==200)
    	{
    	    if(xmlhttpcountries.responseText == "Error")
    	    {
		alert("Country error!");
		return;
    	    }
	    alert("Set Inner HTML");
            dropdown.innerHTML = xmlhttpcountries.responseText;
	}
    }
    xmlhttpcountries.open("POST","country_list.php",true);
    xmlhttpcountries.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xmlhttpcountries.send();
   
}

function sendMsg()
{
    name = document.getElementById("name").value;
    client_tag = document.getElementById("client_tag").value;
    email = document.getElementById("email").value;
    country = document.getElementById("country").value;

    err = "";
    if(name == "")
    {
	err += "Name is not entered.\n";
    }
    if(client_tag == "")
    {
	err += "Device tag is not entered.\n";
    }
    if(email == "")
    {
	err += "Email address is not entered.\n";
    }
    if(email != "" && !validemail("email"))
    {
	err += "Invalid email address.\n";
    }
    if(err != "")
    {
	alert("The following errors occured:\n\n" + err);
	return;
    }
    
     xmlhttp.onreadystatechange=function()
    {
        if (xmlhttp.readyState==4 && xmlhttp.status==200)
        {
    	if(xmlhttp.responseText == "Activation email sent. Check your email.")
    	{
    	    document.getElementById("name").value = document.getElementById("email").value = document.getElementById("client_tag").value = document.getElementById("country").value = "";
	}
    	    
	alert(xmlhttp.responseText);
        }
    }

    getstr = "activate.php";
    args = "name=" + encodeURIComponent(name) + "&client_tag=" + encodeURIComponent(client_tag) + "&email=" + encodeURIComponent(email) + "&country=" + encodeURIComponent(country);
    
    xmlhttp.open("POST",getstr,true);
    xmlhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded")
    xmlhttp.send(args);
}
</script>
<b>Test Unit Activation<br/></b>
Please enter the information required to activate the test device:<br/>
<table>
<tr>
<td>

<table valign="top">
<tr><td>Full Name:</td><td><input id="name" type="text" value="" /></td></tr>
<tr><td>Client Tag:</td><td><input id="client_tag" type="text" value="" /></td></tr>
<tr><td>Email:</td><td><input id="email" type="text" value="" /></td></tr>
<tr><td>Country:</td><td><input id="country" type="text" value="" onchange="javascript:show_consent_form()" /></td></tr>
<tr><td>Country Dropdown:</td><td><select id="countrydropdown" onchange="javascript:show_consent_form()">
  <option value="Other">Other</option>
  <option value="Russia">Russia</option>
  <option value="China">China</option>
</select></td></tr>
<tr><td> </td><td><input type="button" onclick="javascript:sendMsg()" value="Send" /></td></tr>
</table>
</td>
<td>
<img src="http://iclab.org/wp-content/themes/svbtle-child/ICLab-f200.png" />
</td>
</tr>
<tr>
<td>
<div id="consent_form_text">Please select country from the drop-down list...</div>
</td>
</tr>
</table>';
echo
"\n</div>\n";
echo "<div id=\"footer\" align=\"center\">\n";
echo "ICLab";
echo "\n</div>\n";
echo "</body>\n</html>";
?>
