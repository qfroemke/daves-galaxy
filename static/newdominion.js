var originalview = [];
var mousedown = new Boolean(false);
var offset;
var mouseorigin;
var server = new XMLHttpRequest();
var curfleetid = 0;
var curplanetid = 0;
var rubberband;
var curx, cury;
$(document).ready(function() {
   //$(".menu").click(function(){alert("1");});
});

function setxy(evt)
{
  cury = evt.clientY;
  curx = evt.clientX;
}


function changebuildlist(shiptype, change)
{
  var columns = [];
  var rows = [];
  var numships = [];
  var rowtotal = $('#num-'+shiptype).val();
  var hidebuttons = false;
  
  if (rowtotal == ""){
    rowtotal = 0;
  } else {
    rowtotal = parseInt(rowtotal);
  }
  
  rowtotal += change;
  if (rowtotal < 0){
    rowtotal = 0;
  }

  // set the new number of ships to build
  $('#num-'+shiptype).val(rowtotal);
  $("th[id ^= 'col-']").each(function() {
    // get column headers 
    columns.push($(this).attr('id').split('-')[1])
    });
    
  $("td[id ^= 'row-']").each(function() {
    // get row names
    var curshiptype = $(this).attr('id').split('-')[1];
    rows.push(curshiptype)
    });
  //alert(rows);
  for(column in columns){
    var colname = columns[column];
    var qry = 'required-' + colname;
    //alert(qry);
    var coltotal = 0;
    $("td[id ^= '" +qry+ "']").each(function() {
      var curshiptype = $(this).attr('id').split('-')[2];
      //alert(curshiptype);
      var curnumships = parseInt($('#num-'+curshiptype).val());
      //alert(curnumships);
      coltotal += (parseInt($(this).html()) * curnumships);
      });
    var available = parseInt($("#available-"+colname).html());
    coltotal = available-coltotal;
    $("#total-"+colname).html(coltotal);
    if(coltotal < 0){
      $("#total-"+colname).css('color','red');
      hidebuttons=true;
    } else {
      $("#total-"+colname).css('color','white');
    }
    //alert(row);
  }

  // add up ship totals
  var totalships = 0;
  $("input[id ^= 'num-']").each(function() {
    totalships += parseInt($(this).val());
  });

  if(totalships==0){
    hidebuttons = true;
  }

  if(!hidebuttons){
    $("#submit-build").show();
  } else {
    $("#submit-build").hide();
  }

  $("#total-ships").html(totalships);
}

  
  



function rubberbandfromfleet(fleetid,initialx,initialy)
{
  curfleetid = fleetid;
  killmenu();
  
  rubberband.setAttribute('visibility','visible');
  rubberband.setAttribute('x1',initialx);
  rubberband.setAttribute('y1',initialy);
}

function loadnewmenu()
{
  if((server.readyState == 4) && (server.status == 500)){
    w = window.open('');
    w.document.write(server.responseText);
  }
  if ((server.readyState == 4)&&(server.status == 200)){
    var response  = server.responseText;
    buildmenu(); 
    //alert(response);
    $('#menu').html(response);
  }
}

function newmenu(request, method, postdata)
{
  setmenuwaiting();
  sendrequest(request,method,postdata);
  var mapdiv = document.getElementById('mapdiv');
  var newmenu = buildmenu();    
  mapdiv.appendChild(newmenu);
}
function sendrequest(request,method,postdata)
{
  server.open(method, request, true);
  server.setRequestHeader('Content-Type',
                           'application/x-www-form-urlencoded');
  server.onreadystatechange = loadnewmenu;
  if(typeof postdata == 'undefined'){
    server.send(null);
  } else {
    server.send(postdata);
  }
  setmenuwaiting();
}

function handlemenuitemreq(type, requestedmenu, id)
{
  var myurl = "/"+type+"/"+id+"/" + requestedmenu + "/";
  sendrequest(myurl, "GET");
}

function sendform(subform,request)
{
  var submission = new Array();
  for(i in subform.getElementsByTagName('select')){
    var formfield = subform.getElementsByTagName('select')[i];
    if(formfield.type == 'select-one'){
      submission.push(formfield.name + "=" + formfield.options[formfield.selectedIndex].value);
    }
  }
  for(i in subform.getElementsByTagName('button')){
    var formbutton = subform.getElementsByTagName('button')[i];
    submission.push(formbutton.id + "=" + "1");
  }
  for(i in subform.getElementsByTagName('textarea')){
    var textarea = subform.getElementsByTagName('textarea')[i];
    submission.push(textarea.name + '=' + textarea.value);
    }
  for(i in subform.getElementsByTagName('input')){
    var formfield = subform.getElementsByTagName('input')[i];
    if(formfield.name){
      if(formfield.type=="radio"){
        if(formfield.checked){
          submission.push(formfield.name + '=' + formfield.value);
        }
      } else if(formfield.type=="checkbox"){
        if(formfield.checked){
          submission.push(formfield.name + '=' + formfield.value);
        } else {
          submission.push(formfield.name + '=');
        }
      } else {
        submission.push(formfield.name + '=' + formfield.value);
      }
    }
  }
  submission = submission.join('&');
  sendrequest(request,'POST',submission);
}


function zoomcircle(evt,factor)
{
  var p = evt.target;
  var radius = p.getAttribute("r");
  radius *= factor;
  p.setAttribute("r", radius);
}

function planethoveron(evt,planet)
{
  setxy(evt);
  zoomcircle(evt,2.0);
  curplanetid = planet;
}

function planethoveroff(evt,planet)
{
  setxy(evt);
  zoomcircle(evt,.5);
  curplanetid = 0;
}

function fleethoveron(evt,fleet)
{
  setxy(evt);
  zoomcircle(evt,2.0);
}

function fleethoveroff(evt,fleet)
{
  setxy(evt);
  zoomcircle(evt,.5);
}

function buildmenu()
{
  if($('#menu').size()){
    return $('#menu');
  } else {
    var mapdiv = document.getElementById('mapdiv');
    var newmenu = document.createElement('div');
    newmenu.setAttribute('id','menu');
    newmenu.setAttribute('style','position:absolute; top:'+(cury+10)+
                         'px; left:'+(curx+10)+ 'px;');
    newmenu.setAttribute('class','menu');
    setmenuwaiting()
    return newmenu;
  }
}
function dofleetmousedown(evt,fleet)
{
  setxy(evt);
  if(curfleetid==fleet){
    curfleetid=0;
  } else if(!curfleetid){
    var newmenu = buildmenu();
    handlemenuitemreq('fleets', 'root', fleet);
    mapdiv.appendChild(newmenu);
  } else {
    // this should probably be changed to fleets/1/intercept
    // with all the appropriate logic, etc...
    var curloc = getcurxy(evt);
    movefleettoloc(evt,fleet,curloc);
    curfleetid=0;
  }
}

function movefleettoloc(evt,fleet,curloc)
{
  setxy(evt);
  var request = "/fleets/"+fleet+"/movetoloc/";
  var submission = "x=" + curloc.x + "&y=" + curloc.y;

  sendrequest(request,'POST',submission);
}

function doplanetmousedown(evt,planet)
{
  setxy(evt);
  if(curfleetid){
    var request = "/fleets/"+curfleetid+"/movetoplanet/";
    var submission = "planet=" + planet;

    sendrequest(request, 'POST', submission);
    curfleetid=0;
  } else {
    var mapdiv = document.getElementById('mapdiv');
    var newmenu = buildmenu();    
    handlemenuitemreq('planets', 'root', planet);
    mapdiv.appendChild(newmenu);
  } 
}


function domousedown(evt)
{
  setxy(evt);
  if(evt.preventDefault){
    evt.preventDefault();
  }
  killmenu();
  document.body.style.cursor='move';
  mouseorigin = getcurxy(evt);
  mousedown = true;
}

function domouseup(evt)
{
  setxy(evt);
  if(evt.preventDefault){
    evt.preventDefault();
  }
  if(evt.detail==2){
    zoom(evt,.7);
  }
  document.body.style.cursor='default';
  mousedown = false;
  rubberband.setAttribute('visibility','hidden');
  if((curfleetid)&&(!curplanetid)){
    var curloc = getcurxy(evt);
    movefleettoloc(evt,curfleetid,curloc)
    curfleetid=0;
  }
}

function domousemove(evt)
{
  if(evt.preventDefault){
    evt.preventDefault();
  }             
  if(mousedown == true){
    var viewbox = getviewbox(map);
    var neworigin = getcurxy(evt);
    var dx = (mouseorigin.x - neworigin.x);
    var dy = (mouseorigin.y - neworigin.y);
    viewbox[0] = viewbox[0] + dx;
    viewbox[1] = viewbox[1] + dy;
    map.setAttributeNS(null,"viewBox",viewbox.join(" "));
  }
  if(curfleetid){
    var newcenter = getcurxy(evt);
    rubberband.setAttribute('x2',newcenter.x);
    rubberband.setAttribute('y2',newcenter.y);
  }
}

function init(e)
{
  map = document.getElementById('map');
  rubberband = document.getElementById('rubberband');
  offset = map.createSVGPoint();
  originalview = getviewbox(map);
  setaspectratio();
}

function setaspectratio()
{
  var height = parseFloat(window.innerHeight);
  var width = parseFloat(window.innerWidth);
  var vb = originalview.slice();    // force a deep copy
  if(width>height){
    var aspectratio = height/width;
    var centery = vb[1] + (vb[3]/2.0);
    vb[1] = centery - vb[3]*aspectratio/2.0;
    vb[3] = vb[3]*aspectratio;
    map.setAttributeNS(null,"viewBox",vb.join(" "));
  } else {
    var aspectratio = width/height;
    var centerx = vb[0] + (vb[2]/2.0);
    vb[0] = centerx - vb[2]*aspectratio/2.0;
    vb[2] = vb[2]*aspectratio;
    map.setAttributeNS(null,"viewBox",vb.join(" "));
  }
}

function zoom(evt, magnification)
{
  if(evt.preventDefault){
    evt.preventDefault();
  }
  if(evt.detail == 2){
    var newcenter = getcurxy(evt);

    var halfmag = magnification/2.0;
    var viewbox = getviewbox(map);
    var newviewbox = new Array();
    newviewbox[0] = newcenter.x-(viewbox[2]*halfmag);
    newviewbox[1] = newcenter.y-(viewbox[3]*halfmag);
    newviewbox[2] = viewbox[2]*magnification;
    newviewbox[3] = viewbox[3]*magnification;
    map.setAttributeNS(null,"viewBox",newviewbox.join(" "));
  }
}


function getviewbox(doc)
{
  var newviewbox = doc.getAttributeNS(null,"viewBox").split(/\s*,\s*|\s+/);
  for (i in newviewbox){
    newviewbox[i] = parseFloat(newviewbox[i]);
  }
  return newviewbox;
}

function killmenu()
{
  var oldmenu = document.getElementById('menu');
  if(oldmenu){
    oldmenu.parentNode.removeChild(oldmenu);
  }
}


function setmenuwaiting()
{
  $('#menu').html('<div><img src="/site_media/ajax-loader.gif">loading...</img></div>');
}



function getcurxy(evt)
{
  var p = map.createSVGPoint();
  p.x = evt.clientX;
  p.y = evt.clientY;
  p = p.matrixTransform(map.getScreenCTM().inverse());
  return p;
}
