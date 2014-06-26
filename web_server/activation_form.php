<?php

echo "<html>\n<head>\n";
echo "<title>\n";
echo "ICLab Test Unit Activation Form";
echo "</title>\n";
echo "<link rel=\"stylesheet\" type=\"text/css\" href=\"css/general_style.css\" />\n";
echo "</head>\n";
echo "<body>";
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
}
else
{	// code for IE6, IE5
    xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
}
function validemail(email) {
 
   var reg = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
   var address = document.getElementById(email).value;
   if(reg.test(address) == false) {
      return false;
   }
   return true;
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
<tr><td>Country:</td><td><input id="country" type="text" value="" /></td></tr>
<tr><td> </td><td><input type="button" onclick="javascript:sendMsg()" value="Send" /></td></tr>
</table>
</td>
<td>
<img src="http://iclab.org/wp-content/themes/svbtle-child/ICLab-f200.png" />
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