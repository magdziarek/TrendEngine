var coordinates = document.getElementById('coords'),
dataset_name = document.forms["form"]["dataset_name"],
isPolytrend = document.getElementById("isPolytrend"),
isDbest = document.getElementById("isDbest"),
start = document.forms["form"]["from_year"],
end = document.forms["form"]["to_year"],
breakpoint_no = document.forms["form"]["breakpoint_no"],
first_level_shift = document.forms["form"]["first_level_shift"],
second_level_shift = document.forms["form"]["second_level_shift"];

function setDbest(){
let dbestDiv = document.getElementById('dbestDiv');
ptDiv.style.display = 'none';
dbestDiv.style.display = '';
isPolytrend.value = "no";
isDbest.value = "yes";
}
function setPt(){
let ptDiv = document.getElementById('ptDiv');
dbestDiv.style.display = 'none';
ptDiv.style.display = '';
isPolytrend.value = "yes";
isDbest.value = "no";
}

function updateValues(collection){
if (collection == "NASA/GIMMS/3GV0"){
  console.log(collection);
  first_level_shift.value = 0.1;
  first_level_shift.innerHTML = 0.1;
  second_level_shift.value = 0.2;
  second_level_shift.innerHTML = 0.2;
}
else{
  console.log(collection);
  first_level_shift.value = 500;
  first_level_shift.innerHTML = 500;
  second_level_shift.value = 1000;
  second_level_shift.innerHTML = 1000;
}
}

function validateForm() {
console.log('validating form');

if (start.value > end.value) {
  alert("Start date must be greater than end date.");
  return false;
}
else if (start.value == '' || end.value == ''){
  alert("Please input dates.");
  return false;  
}
if(dataset_name.value == "NASA/GIMMS/3GV0"){
  if(start.value < 1982 || start.value > 2012){
    alert('Check start date for GIMMS dataset. It shouldn\'t be earlier than 1982 and no later than 2013.');
    return false;
  }
  else if(end.value < 1982 || end.value > 2013){
    alert('Check end date for GIMMS dataset. It shouldn\'t be earlier than 1982 and no later than 2013.');
    return false;
  }
}
else {
  if(start.value < 2001 || start.value > 2019){
    alert('Check start date for MODIS dataset. It shouldn\'t be earlier than 2001 and no later than 2019.');
    return false;
  }
  else if(end.value < 2001 || end.value > 2019){
    alert('Check end date for MODIS dataset. It shouldn\'t be earlier than 2001 and no later than 2019.');
    return false;
  }
}
if (dataset_name.value == 0 || document.forms["form"]["coords"].value == ''){
  alert("You must specify the dataset name and coordinates of your area of interest");
  return false;
}
if (isDbest.value == "yes" && breakpoint_no.value == ''){
  alert('How many breakpoints?')
  return false;
}
}

///////////////// MAKE A MAP WITH DRAW CONTROL FOR MARKING AREA OF INTEREST ////////////////////////////
var map = document.getElementById('map'),
leafletMap = L.map(map).setView([52.410021807429814, 18.620109558105472], 5);

var mapLink = 
'<a href="http://openstreetmap.org">OpenStreetMap</a>';
L.tileLayer(
'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', 
{
attribution: '&copy; ' + mapLink + ' Contributors',
maxZoom: 15,
minZoom: 6
}
).addTo(leafletMap);
//add map controls
var drawnItems;
L.control.scale().addTo(leafletMap);
//add drawing utilities, only marker and polygon can be drawn
var drawnItems = new L.FeatureGroup();
leafletMap.addLayer(drawnItems);
var drawControl = new L.Control.Draw({draw: {
polyline: false,
polygon: false,
rectangle: true,
circle: false,
marker: true
},
edit:{
featureGroup: drawnItems
}
});
leafletMap.addControl(drawControl);
//when a marker is drawn, display its coordinates
leafletMap.on(L.Draw.Event.CREATED, function (e) {
let type = e.layerType,
  layer = e.layer;
if (type === 'marker'){
  drawnItems.addLayer(layer);
  let latLng = layer.getLatLng();
  coordinates.innerHTML = '[' + latLng.lng + ',' + latLng.lat + ']';
}
if (type === 'rectangle'){
  drawnItems.addLayer(layer);
  let latLng = layer.getLatLngs()[0];
  coordinates.innerHTML = '[[['+latLng[0].lng +','+ latLng[0].lat + '],[' + latLng[1].lng+ ',' + latLng[1].lat + '],[' + 
    latLng[2].lng + ', ' + latLng[2].lat + '], [' + latLng[3].lng + ', ' + latLng[3].lat + ']]]';
}
});  