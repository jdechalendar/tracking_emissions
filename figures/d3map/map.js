//var fileNm_data = "data/graph_plot_data.json";
// var fileNm_data = "data/graph_CO2.json";
//var fileNm_data = "data/graph_SO2.json";
//var fileNm_data = "data/graph_NOx.json";
//var fileNm_data = "data/EBA_diffs.json";
// var fileNm_data = "data/AMPD_diffs_CO2.json";
// var fileNm_data = "data/AMPD_diffs_SO2.json";
// var fileNm_data = "data/AMPD_diffs_NOX.json";

var poll = "CO2";
var variable = "E";
var fileNm_data = "data/graph_"+variable+"_"+poll+"i.json";
var fileNm_data2 = "data/graph_CO2_CO2i.json";


// initialize some global variables - values will be set when reading the file
var colorModeAuto = '';
var fieldRadius = '';
var fieldLineWidth = '';
var fieldCircle = '';
var fieldLineColor = '';

var width = 960,
    height = 670,
    heightMap = 600;

// Note that the subgrid data I am supplying has not been projected
// I could do that by preprocessing in the future
var proj = d3.geoAlbers().scale(1280).translate([480, 300]);

var path = d3.geoPath()
//    .projection(proj);

// Define containers here so layering is correct
var svg = d3.select("body").append("svg")
  .attr("width", width)
  .attr("height", height);
svg.append("rect")
  .attr("width", width)
  .attr("height", height)
  .attr("class", "sea");
var mapContainer = svg.append("svg")
  .attr("width", width)
  .attr("height", heightMap);
var baGraphContainer = svg.append("svg")
  .attr("width", width)
  .attr("height", heightMap);

// Add buttons
var buttonDiv = d3.select("body").append("div")

if (false) {
buttonDiv.append("input")
    .attr("name", "saveButton")
    .attr("type", "button")
    .attr("value", "Save node positions")
    .attr("onclick", "saveXY()");

buttonDiv.append("input")
    .attr("name", "loadButton")
    .attr("type", "button")
    .attr("value", "Load node positions")
    .attr("onclick", "loadXY()");

buttonDiv.append("input")
    .attr("name", "saveButton2")
    .attr("type", "button")
    .attr("value", "Save label positions")
    .attr("onclick", "saveXY2()");
}

options = [];
for (const poll of ["CO2", "SO2", "NOX"]){
  for (const variable of ["E", poll]) {
    options.push("data/graph_"+variable+"_"+poll+"i.json");
  }
}
var dropdown = buttonDiv.append("select")
  .on("change", function() { drawMap(d3.select(this).property('value')); });
dropdown.selectAll("option")
    .data(options)
  .enter().append("option")
    .attr("value", function(d) {return d;})
    .text(function(d) {return d;});


// Create background map
//d3.json("data/eGRID2016_Subregions-topo.json").then(function(egrid) {
d3.json("data/us-10m.v1.json").then(function(us) {

  // Plot the land area
  mapContainer.append("path")
    .datum(topojson.merge(us, us.objects.states.geometries.filter(
        function(d) { return true; })))
      .attr("class", "land")
      .attr("d", path);
  // add state lines here instead
  mapContainer.append("path").
    datum(topojson.mesh(us, us.objects.states,
        function(a, b) { return a !== b; }))
    .attr("class", "border border--egrid")
    .attr("d", path);
  // Add lines for the Interconnects
  mapContainer.append("path")
    .attr("class", "interconnect")
    .attr("d", "M420 50 L420 370 L320 530 M420 370 L650 530")
});

// Create network on top of map
var node = baGraphContainer.selectAll(".node");
var label2 = baGraphContainer.selectAll(".label2");
var link = baGraphContainer.selectAll(".link");
var defs = baGraphContainer.append("defs");

defs.append('marker')
    .attr('id', "legendArrow")
    .attr('viewBox', '-0 -2.5 5 5')
    .attr('refX', 0)
    .attr('orient','auto')
    .attr('markerUnits', 'strokeWidth')
    .append('svg:path')
    .attr('d', 'M 3,0 L 0 ,1.5 L 0,-1.5 z')
    .attr('fill', "grey");

// Scales are functions that map from an input "domain" to an output "range".
// For circle, se sqrt so that area of the circle will be prop to the value
var radius = d3.scaleSqrt().range([5, 50]);
var radLimText = 19;  // cutoff radius to decide whether text is in or out of
                      // node
var radLimTextNumber = 21;  // cutoff radius to decide whether we add the value
var lineWidth = d3.scaleLinear().range([3, 15])
var circleColor = d3.scaleThreshold()
  .domain([100, 200, 300, 400, 500, 600, 700, 900])
  .range(d3.schemeRdYlGn[9].reverse());

// legend for colors
var leg = svg.append("g")
  .attr("transform", "translate(430,"+ (heightMap+30)+")")
  .attr("class", "legend")
  .attr("id", "leg");
leg.append("text")
  .attr("class", "legtitle")
  .attr("y", 25)
  .style("text-anchor", "start");

// legend for circles
var leg2 = svg.append("g")
    .attr("class", "legend")
    .attr("id", "leg2")
    .attr("transform", "translate(120, "+ (heightMap+40)+")");
leg2.append("text")
  .attr("class", "legtitle")
  .attr("y", 15)
  .style("text-anchor", "middle");

// legend for links
var leg3 = svg.append("g")
  .attr("class", "legend")
  .attr("transform", "translate(320, "+ (heightMap+40)+")")
  .attr("id", "leg3");
leg3.append("text")
  .attr("class", "legtitle")
  .attr("y", 15)
  .style("text-anchor", "middle");

// title
var title = svg.append("g")
  .attr("transform", "translate("+(1.2*width/2)+", 20)")
  .attr("class", "graphtitle")
  .append("text")
    .attr("y", 15)
    .style("text-anchor", "middle");

var wecc_title = svg.append("g")
  .attr("transform", "translate(120, 470)")
  .attr("class", "graphsubtitle")
  .append("text")
    .attr("y", 15)
    .style("text-anchor", "middle");
var eic_title = svg.append("g")
  .attr("transform", "translate(750, 70)")
  .attr("class", "graphsubtitle")
  .append("text")
    .attr("y", 15)
    .style("text-anchor", "middle");

var ggraph = [];

var colorExtent = [];

function drawMap(fileNm_data) {
d3.json(fileNm_data).then(function(graph) {
  // console.log(graph)
  ggraph = graph; //make this available from the console

  // unpack options
  colorModeAuto = graph.meta.colorModeAuto;
  fieldRadius = graph.meta.fieldRadius;
  fieldLineWidth = graph.meta.fieldLineWidth;
  fieldCircle = graph.meta.fieldCircle;
  fieldLineColor = graph.meta.fieldLineColor;

  // set domain for radius scale
  radius.domain(d3.extent(graph.nodes.map(function(d){
    return d[fieldRadius]; })))

  // set domain for color scale
  colorExtent = d3.extent(graph.nodes.map(function(d){
    return (fieldCircle in d ? d[fieldCircle] : 0); }));
  if (colorModeAuto) {
    circleColor.domain(linspace(colorExtent[0], colorExtent[1],10).slice(1,9));
  }

  // set domain for width of connections
  if ("links" in graph) {
      lineWidth.domain(d3.extent(graph.links.map(function(d){
        return d[fieldLineWidth]; })))
  }

  // get (x,y) coords for the nodes by applying our projection
  graph.nodes.map(function(d, i){[d["x"], d["y"]] = proj(d.coords)});
  graph.labels.map(function(d, i){[d["x"], d["y"]] = proj(d.coords)});


  if ("links" in graph) {
    graph.links.forEach(function(d) {
        d.sourceNode = graph.nodes[d.source];
        d.targetNode = graph.nodes[d.target];
      });

    // Note: for markers the typical d3 update pattern does not seem to work
    // (because they are part of the svg defs?) In any case, just starting over
    // from scratch is easier
    defs.select(".arrow").remove();
    var arrow = defs.selectAll(".arrow").data(graph.links);
    arrow.enter().append('marker')
          .attr("class", "arrow")
      .merge(arrow)
        .attr('id', function(d){return "arrow"+d.source+"_"+d.target})
        .attr('viewBox', '-0 -2.5 5 5')
        .attr('refX', 0)
        .attr('orient','auto')
        .attr('markerUnits', 'strokeWidth')
        .append('svg:path')
        .attr('d', 'M 3,0 L 0.3 ,1.5 L 0.3,-1.5 z')
        .attr('fill', function(d) {
          return (d[fieldLineColor] ? circleColor(d[fieldLineColor]) :
                  "grey"); });

    var linkSel = baGraphContainer.selectAll(".link").data(graph.links);

    linkSel.exit().remove();
    linkSel.enter().append("g").append("path")
      .merge(linkSel)
      .attr("class", "link")
      .attr("marker-end", function(d){
          return "url(#arrow"+d.source+"_"+d.target+")"})
      .attr("stroke", function(d) {
        return (d[fieldLineColor] ? circleColor(d[fieldLineColor]) : "grey"); })
      .style("stroke-width", function(d) {
        return (d[fieldLineWidth] ? lineWidth(d[fieldLineWidth]) : 3); });

  }

  // update pattern is slightly more complex for the nodes so I break it up
  
  // UPDATE SEL
  var nodeSel = baGraphContainer.selectAll(".node").data(graph.nodes);

  // EXIT SEL
  nodeSel.exit().remove();

  // ENTER SEL
  var nodeEnter = nodeSel.enter()
      .append("g")
      .attr("class", "node");
  nodeEnter.append("circle");
  nodeEnter.append("text");

  // MERGED ENTER + UPDATE SEL
  nodeSel = nodeEnter.merge(nodeSel);
  nodeSel.attr("transform", function(d) {
        return "translate(" + d.x + "," + d.y + ")"; })
      .each(updateLinePos)
      .call(d3.drag().on("drag", dragged));
  nodeSel.select("circle")
    .attr("r", function(d){
      return (d[fieldRadius] ? radius(d[fieldRadius]) : 5); })
    .attr("fill", function(d){
      return (d[fieldCircle] ? circleColor(d[fieldCircle]) :
              "grey"); })
    .attr("stroke", "black");

  nodeSel.select("text").selectAll("tspan").remove();
  let nodeText = nodeSel.filter((d) => (d[fieldRadius] ? radius(d[fieldRadius])
                         > radLimTextNumber : false))
    .select("text")
      .attr('class', 'label')
      .attr('dy', '-.3em')
      .text(""); // make sure we clean up from a previous iteration
   nodeText.append("tspan")
        .text((d)=>d.shortNm)
   nodeText.append("tspan")
//        .text((d) => `${d.E_D.toFixed(0)} ${graph.meta.unit}`)
        .text((d) => d.E_D.toFixed(0))
        .attr('x', '0')
        .attr('dy', '1.2em');

  nodeSel.filter((d) => (d[fieldRadius] ? radius(d[fieldRadius])
                         <= radLimTextNumber : true))
    .select("text")
      .attr('class', 'label')
      .attr('dy', '0.3em')
      .text(function(d) {
        let rad = (d[fieldRadius] ? radius(d[fieldRadius]) : 5);
        if (rad > radLimText)
          return d.shortNm;
        else { return ""; } });


  var label2Sel = baGraphContainer.selectAll(".label2").data(graph.labels);
  label2Sel.exit().remove();
  
  var label2Enter = label2Sel.enter()
    .append("g")
    .attr("class", "label2");
  label2Enter.append("text")
    .attr('class', 'label-small')
    .attr('dy', '0.3em');

  label2Sel = label2Enter.merge(label2Sel);
  label2Sel.attr("transform", function(d) {
      return "translate(" + d.x + "," + d.y + ")"; })
    .call(d3.drag().on("drag", dragged2));
  label2Sel.select("text").text(function(d) {
      var rad = (d[fieldRadius] ? radius(d[fieldRadius]) : 5);
      if (rad <= radLimText)
        return d.shortNm;
      else { return ""; }
    });


  // Legend for colors
  var x = d3.scaleLinear()
      .domain(colorExtent)
      .range([0, 500]);

  var xAxis = d3.axisTop(x)
      .tickSize(5)
      .tickValues(circleColor.domain());

  leg.call(xAxis);
  leg.select(".domain").remove();
  d3.select("#leg").select(".legtitle").text(graph.meta.legColorTitle);

  legSel = leg.selectAll("rect")
    .data(circleColor.range().map(function(color) {
        d = circleColor.invertExtent(color);
        if (d[0] == null) d[0] = x.domain()[0];
        if (d[1] == null) d[1] = x.domain()[1];
        return d;
      }));
  
  legSel.enter()
        .append("rect")
    .merge(legSel)
      .attr("height", 8)
      .attr("x", function(d) { return x(d[0]); })
      .attr("width", function(d) { return Math.abs(x(d[1]) - x(d[0])); })
      .attr("fill", function(d) { return circleColor(d[0]); });

  // Legend for circle size
  var maxRad = radius.domain()[1];
  d3.select("#leg2").select(".legtitle").text(graph.meta.legCircleTitle);

  leg2Sel = leg2.selectAll("g")
    .data([0.1*maxRad, 0.35*maxRad, 0.9*maxRad]);
  leg2Enter = leg2Sel.enter().append("g");

  leg2Enter.append("circle");

  leg2Enter.append("text")
    .attr("class", "legend-text")
    .attr("dy", "1.3em");

  leg2Sel = leg2Enter.merge(leg2Sel);
  leg2Sel.select("circle")
    .attr("cy", function(d) { return -radius(d); })
    .attr("r", radius);
  leg2Sel.select("text")
    .attr("y", function(d) { return -2 * radius(d); })
    .text(d3.format(".1s"));

  // legend for link size
  if ("links" in graph) {
      d3.select("#leg3").select(".legtitle").text(graph.meta.legLineTitle);

    var maxWidth = lineWidth.domain()[1];
    leg3Sel = leg3.selectAll("g")
        .data([
          {"w":0.15*maxWidth, "l":120},
          {"w":0.5*maxWidth, "l":78},
          {"w":maxWidth, "l":43}]);
    leg3Enter = leg3Sel.enter().append("g");

    leg3Enter.append("path")
      .attr("stroke", "grey");

    leg3Enter.append("text")
       .attr("class", "legend-text")
       .attr("dy", "0.5em");
    leg3Sel = leg3Enter.merge(leg3Sel);
    leg3Sel.select("text")
      .attr("y", function(d) { return -14-lineWidth(d.w); })
      .attr("x", function(d) { return d.l-60; })
      .text(function(d){return d3.format(".2s")(d.w);});
    leg3Sel.select("path")
      .attr("marker-end", function(d){return "url(#legendArrow)"})
      .attr('d', function(d) {
        return ('M ' + (d.l-48) + ',' + (-5-lineWidth(d.w)/2) + ' L -48,'
                + (-5-lineWidth(d.w)/2) + '');
      })
      .style("stroke-width", function(d) {lineWidth(d.w) })
      .attr("stroke-width", function(d){return lineWidth(d.w);});
  }
  // title
  let total = graph.nodes.map(el=>el.E_D).reduce((a,c)=>a+c, 0);
  title.text(`2016 ${graph.meta.title} CONSUMPTION
              (${total.toFixed(0)} ${graph.meta.unit} total)`);
  let total_wecc = graph.nodes.filter(el=>el.interconnect=='wecc')
        .map(el=>el.E_D).reduce((a,c)=>a+c, 0);
  let total_eic = graph.nodes.filter(el=>el.interconnect=='eic')
        .map(el=>el.E_D).reduce((a,c)=>a+c, 0);
  
  wecc_title.selectAll("tspan").remove();
  wecc_title.append("tspan").text("Western Interconnect");
  wecc_title.append("tspan")
        .text(`${total_wecc.toFixed(0)} ${graph.meta.unit}`)
        .attr('x', '0')
        .attr('dy', '1.2em');

  eic_title.selectAll("tspan").remove();
  eic_title.append("tspan").text("Eastern Interconnect");
  eic_title.append("tspan")
        .text(`${total_eic.toFixed(0)} ${graph.meta.unit}`)
        .attr('x', '0')
        .attr('dy', '1.2em');
});
}

function dragged(d) {
  d.x = d3.event.x, d.y = d3.event.y;
  // update node position
  d3.select(this).attr("transform", function(d) {
    return "translate(" + d.x + "," + d.y + ")"; })
  updateLinePos(d);  // update line position
}

function dragged2(d) {
  d.x = d3.event.x, d.y = d3.event.y;
  // console.log([d3.event.x, d3.event.y])
  d3.select(this).attr("transform", function(d) {
    return "translate(" + d.x + "," + d.y + ")"; })
}

// helper function to update line position
function updateLinePos(node) {
  var line = d3.selectAll(".link");
  line.filter(function(l) {return l.sourceNode === node; })
    .attr('d', calcLinePos);
  line.filter(function(l) { return l.targetNode === node; })
    .attr('d', calcLinePos);
}

function calcLinePos(d) {
  const deltaX = d.targetNode.x - d.sourceNode.x;
  const deltaY = d.targetNode.y - d.sourceNode.y;
  const dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
  const normX = deltaX / dist;
  const normY = deltaY / dist;
  const sourcePadding = (d.sourceNode[fieldRadius] ? radius(d.sourceNode[fieldRadius]) : 5);
  const targetPadding = (
    (d.targetNode[fieldRadius] ? radius(d.targetNode[fieldRadius]) : 5)
    + 2 * (d[fieldLineWidth] ? lineWidth(d[fieldLineWidth]) : 3)
    );
  const sourceX = d.sourceNode.x + (sourcePadding * normX);
  const sourceY = d.sourceNode.y + (sourcePadding * normY);
  const targetX = d.targetNode.x - (targetPadding * normX);
  const targetY = d.targetNode.y - (targetPadding * normY);
  return `M${sourceX},${sourceY}L${targetX},${targetY}`;
}

// helper function to download the node coordinates
function saveXY() {
  var posList = {};
   // select each node - get its shortNm and its position transform
  d3.selectAll(".node").each(function(d) {
     // un-project coords
    posList[d.shortNm] = proj.invert([d.x, d.y]); });
  var dummy = document.createElement("a");
  var encodedUri = encodeURI(
    "data:text/json;charset=utf-8," + JSON.stringify(posList));
  dummy.setAttribute("href", encodedUri);
  dummy.setAttribute("download", "xycoords.json");
  document.body.appendChild(dummy);
  dummy.click(); // This will download the data file
}

// helper function to load previously saved node coordinates
function loadXY() {
  d3.json("data/xycoords.json").then(function(readList) {
    d3.selectAll(".node").each(function(d) {
      d.x = readList[d.shortNm][0], d.y = readList[d.shortNm][1];
      [d.x, d.y] = proj([d.x, d.y]) // project coords
      d3.select(this).attr("transform", function(d) {
        // update
        return "translate(" + d.x + "," + d.y + ")"; })
      updateLinePos(d);
    })
  });
}

// helper function to download the node coordinates
function saveXY2() {
  var posList = {};
   // select each node - get its shortNm and its position transform
  d3.selectAll(".label2").each(function(d) {
     // un-project coords
    posList[d.shortNm] = proj.invert([d.x, d.y]); });
  var dummy = document.createElement("a");
  var encodedUri = encodeURI(
    "data:text/json;charset=utf-8," + JSON.stringify(posList));
  dummy.setAttribute("href", encodedUri);
  dummy.setAttribute("download", "xycoords_lab.json");
  document.body.appendChild(dummy);
  dummy.click(); // This will download the data file
}

var linspace = function(start, stop, n) {
  var arr = [];
  var curr = start;
  var step = (stop - start) / (n - 1);
  for (var i = 0; i < n; i++) {
    arr.push(Math.round(curr + (step * i)));
  }
  return arr;
}


drawMap(fileNm_data);
