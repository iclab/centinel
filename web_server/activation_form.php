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

	    

            document.getElementById("consent_agreement_checkbox").checked = false;
    	    document.getElementById("consent_form_text").style.visibility="hidden";
	    document.getElementById("consent_textarea").value = xmlhttpconsent.responseText;
	    document.getElementById("consent_div").style.display = "block";
	    var url = "http://freedomhouse.org/report/freedom-world/2014/"+country+"-0";
	    document.getElementById("stats_iframe").src = url;
	    
	    if (country == "Other") 
            {
		document.getElementById("country_other_paragraph").style.display = "block";
	    } 
            else
	    {
		document.getElementById("country_other_paragraph").style.display = "none";
	    }
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
    dropdown = document.getElementById("countrydropdown");
    country = dropdown.options[dropdown.selectedIndex].text;
    if (country == "Other")
    {
	country = document.getElementById("country_other").value;
    }

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

    
    if (country == "")
    {
        err += "Country has not been entered.\n";
    }

    if (!consent_agreement_checkbox.checked)
    {
        err += "Consent form has not been agreed to.\n";
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
<tr><td>Country Dropdown:</td><td><select id="countrydropdown" onchange="javascript:show_consent_form()"></select></td></tr>
<tr><td><td>
<div id="consent_div" style="display: none" align="center">
<p id="country_other_paragraph" align="left" style="display: none">
Country: <input type="text" id="country_other" value="" />
</p>
<textarea id="consent_textarea" style.visibility="hidden" readonly rows="20" cols="80">
</textarea>
<br>
<iframe id="stats_iframe" width="625" height="300"></iframe>
<br>
<input type="checkbox" id="consent_agreement_checkbox" value="agreed" /> I agree to these terms
</div></td></td></tr>
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
