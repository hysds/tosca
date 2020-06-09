function get_geojson(coords, location_type) {
  var coords_geojson = [];
  for (var i=0; i<coords.length; i++) {
    if (i%2 == 0) {
      var point = [ coords[i], coords[i+1] ];
      coords_geojson.push(point);
    }
  }
  if (location_type == 'linestring') {
    var geojson_type = 'LineString';
  }else {
    var geojson_type = 'Polygon';
    coords_geojson = [ coords_geojson ];
  }
  return {
    'type': 'Feature',
    'properties': {
      'name': 'test name',
      'amenity': 'test amenity',
      'popupContent': 'This is the popup content'
    },
    'geometry': {
      'type': geojson_type,
      'coordinates': coords_geojson
    }
  };
}


function jq( myid ) {
  return "#" + myid.replace( /(:|\.|\[|\])/g, "\\$1" );
}

function get_tile_max_zoom(tile_zoom, ind) {
  if (tile_zoom.length==0){
    max_zoom = 8;
  }
  else{
    max_zoom = parseInt(tile_zoom[ind]);
  }
  return max_zoom;
}

define(
[
  'bower_components/flight/lib/component',
  'bower_components/flight/lib/compose',
  'js/components/facetViewMenuComponent',
  'js/mixins/backMap',
  'js/mixins/thumbView'
],
function(defineComponent,compose,FacetViewMenu,backMap,thumbView){
  return defineComponent(mainAppView);

  function mainAppView(){
    
    this.after('initialize',function(){  
      var that = this;
      this.overrideFacetViewDefaults();
      //alright, after the main view component is init, lets start doing stuff.
      this.injectCSS();//inject our own CSS into the <head>
      this.initFacetView();//and kick off facetView, then fork the browse options to it's own component...
      console.log('init');
      //testing
      $('.flipMapButton').on('click',function(){
        $('#imageTooltip').hide();
        $('#backSide').css('width',$('#frontSide').width()+30)
        $('#flipCard').toggleClass('flipped');
        if($('#flipCard').hasClass('flipped')){
          $('#facetview_filters').addClass('isBack');
        }
        else{
          $('#facetview_filters').removeClass('isBack')
        }
        if(typeof that._map != "undefined")
          that._map.invalidateSize();
        //setTimeout(function(){alert('d');that._map.panTo(new L.LatLng(0,0));},3500);
      });

      compose.mixin(this,[backMap]);
      //ok init our new map we mixed in
      this.initMap('backMap'); //and we pass in the dom ID string that leaflet will attach to...
      //and now mixin our gridview
      compose.mixin(this,[thumbView]);
      this.initThumbView();
    });
    
    this.overrideFacetViewDefaults = function(){
      var that = this;
      //anything to override jquery.facetview.js native behaviors, thus not to ever modify their source code
      jQuery.extend({
        //rewrote the native jquery.facetview geturlvars method because it's crap....
        getUrlVars: function() {
          var params = new Object;
          var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
          for ( var i = 0; i < hashes.length; i++ ) {
            hash = hashes[i].split('=');
            if ( hash.length > 1 ) {
              if ( hash[1].replace(/%22/gi,"")[0] == "[" || hash[1].replace(/%22/gi,"")[0] == "{" ) {
                hash[1] = hash[1].replace(/\%22/g,'"');
                hash[1] = hash[1].replace(/\%20/g,' ');
                hash[1] = hash[1].substring(hash[1].length-1) == '/' ? hash[1].substring(0,hash[1].length-1) : hash[1];
                console.log('hash is',hash)
                var newval = JSON.parse(hash[1]);
              } else {
                var newval = unescape(hash[1].replace(/%22/gi,'"'));
              }
              params[hash[0]] = newval;
            }
          }
          return params;
        },
        getUrlVar: function(name){
          return jQuery.getUrlVars()[name];
        }
      });
      
      $.ajaxSetup({
        global:true
      });
      
      //intercept AJAX requests::
      $(document).ajaxComplete(function(e, xhr, settings){
          console.log('request success',xhr.responseJSON,e,settings)
          var json = xhr.responseJSON;
          if(typeof json != "undefined"){
            //ok it's json, now what!?
            if(typeof json.hits != "undefined"){
              //ok it's the response we were looking for. Now handle some data...
              that.handleInterceptedJSON(json);
              $(document).trigger('updatedResultList')
            }
          }
      });
    };
    
    this.handleInterceptedJSON = function(data){
      //takes a JSON search response, makes sure it's a search from jquery.facetview, then gives us the resp to do etc with
      if(typeof this._map != 'undefined'){
        //ok, we have some kind of map! Let's poop out some results there.
        this.plotMapResult(data.hits);
      }
      console.log('this res',data);
    };
    
    this.initFacetView = function(){
      var _this = this;
          
      //ok attach this crufty badboy...
      
      //Tags.bootstrapVersion = "2";

      function set_left_margin() {
        return ($(window).width() - $(this).width())/2;
      }

      function add_user_tag(es_index, id, tag) {
        ////console.log("Adding tag '" + tag + "' to " + id);
        $.ajax({
          type: 'POST',
          url: "{{ url_for('services/user_tags.add_user_tag') }}",
          data: { es_index: es_index, id: id, tag: tag }
        }); 
      }
      
      function remove_user_tag(es_index, id, tag) {
        //console.log("Removing tag '" + tag + "' to " + id);
        $.ajax({
          type: 'POST',
          url: "{{ url_for('services/user_tags.remove_user_tag') }}",
          data: { es_index: es_index, id: id, tag: tag }
        }); 
      }

      // global backdrop
      var backdrop = null;
    
      $('.facet-view-simple').facetview({
        search_url: "{{ url_for('services/query.query', dataset=config['ES_INDEX']) }}?",
        search_index: 'elasticsearch',
        facets: [
          //{'field':'metadata.priority', 'display': 'product priority'},
          //{'field':'metadata.context.job_priority', 'display': 'job priority'},
          {'field':'dataset', 'display': 'dataset'}, 
          {'field':'metadata.platform', 'display': 'platform'},
          {'field':'metadata.sensor.untouched', 'display': 'sensor'},
          {'field':'system_version', 'display': 'dataset version'}, 
          {'field':'metadata.user_tags.untouched', 'display': 'user tags'},
          {'field':'metadata.tags.untouched', 'display': 'machine tags'},
          {'field':'starttime', 'display': 'start date', 'type': 'date'},
          {'field':'endtime', 'display': 'stop date', 'type': 'date'},
          {'field':'temporal_span', 'display': 'temporal span (days)', 'type': 'number'},
          {'field':'continent.untouched', 'display': 'continent'},
          {'field':'city.country_name.untouched', 'display': 'country'},
          {'field':'city.admin1_name.untouched', 'display': 'region'},
          {'field':'city.admin2_name.untouched', 'display': 'subregion'},
          {'field':'city.name.untouched', 'display': 'city'},
          {'field':'metadata.dfas.RequestorUserId.untouched', 'display': 'requestor'},
          {'field':'dataset_type.untouched', 'display': 'type'},
          {'field':'dataset_level.untouched', 'display': 'level'},
          {'field':'metadata.corrections.untouched', 'display': 'corrections'},
          {'field':'metadata.spacecraftName.untouched', 'display': 'spacecraft'},
          {'field':'metadata.direction', 'display': 'orbit direction'},
          {'field':'metadata.lookDirection', 'display': 'look direction'},
          //{'field':'metadata.orbitNumber', 'display': 'orbit number', 'type': 'number'},
          {'field':'metadata.scene_count', 'display': 'stitched scenes count', 'type': 'number'},
          {'field':'metadata.orbit_type', 'display': 'input orbit type'},
          {'field':'metadata.orbitRepeat', 'display': 'orbit repeat'},
          {'field':'metadata.trackNumber', 'display': 'track number', 'type': 'number'},
          {'field':'metadata.swath', 'display': 'subswath', 'type': 'number'},
          {'field':'metadata.beamID', 'display': 'beam ID'},
          {'field':'metadata.beamNumber', 'display': 'beam number', 'type': 'number'},
          {'field':'metadata.predicted_phase_unwrapping_bucket', 'type':'number','display': 'Phase Unwrapping Quality (Predicted)'},
          //{'field':'metadata.sensingStart', 'display': 'sensing date', 'type': 'date'},
          //{'field':'metadata.latitudeIndexMin', 'display': 'lat index min', 'type': 'number'},
          //{'field':'metadata.latitudeIndexMax', 'display': 'lat index max', 'type': 'number'},
          {'field':'metadata.frameID', 'display': 'frame ID', 'type': 'number'},
          {'field':'metadata.timestep_count', 'display': 'timesteps', 'type': 'number'},
          //{'field':'metadata.dfdn.ProductType.untouched', 'display': 'product type'},
          {'field':'metadata.dfdn.AcquistionMode', 'display': 'acquisition mode'},
          {'field':'metadata.dfdn.LookSide', 'display': 'look side'},
          {'field':'metadata.dfdn.DeliveryMode', 'display': 'delivery mode'},
          {'field':'metadata.version', 'display': 'version'},
          {'field':'metadata.source', 'display': 'source archive'},
          {'field':'metadata.dataset_type', 'display': 'source datatype'}
        ],
        time_fields: [
          'starttime',
          'endtime',
          'metadata.sensingStart',
          'metadata.sensingStop'
        ],
        bucketed_fields: [
        ],
        location_field: 'location',
        json_fields: [
          'metadata.user_tags',
          'metadata.tile_max_zoom',
          'metadata.tile_layers',
          'images'
        ],
        filterchoice_result_fields: {
          'metadata.version': 'metadata.version',
          'metadata.tags': 'metadata.tags.untouched',
          'metadata.corrections': 'metadata.corrections.untouched',
          'continent': 'continent.untouched',
          'city.admin2_name': 'city.admin2_name.untouched',
          'city.admin1_name': 'city.admin1_name.untouched',
          'city.country_name': 'city.country_name.untouched',
          'city.name': 'city.name.untouched',
          'metadata.spacecraftName': 'metadata.spacecraftName',
          'metadata.direction': 'metadata.direction',
          'metadata.lookDirection': 'metadata.lookDirection',
          'metadata.orbit_type': 'metadata.orbit_type',
          'metadata.orbitNumber': 'metadata.orbitNumber',
          'metadata.orbitRepeat': 'metadata.orbitRepeat',
          'metadata.trackNumber': 'metadata.trackNumber',
          'metadata.beamNumber': 'metadata.beamNumber',
          'metadata.predicted_phase_unwrapping_bucket':'metadata.predicted_phase_unwrapping_bucket',
          'metadata.latitudeIndexMin': 'metadata.latitudeIndexMin',
          'metadata.latitudeIndexMax': 'metadata.latitudeIndexMax',
          'metadata.frameID': 'metadata.frameID',
          'metadata.dfdn.ProductType': 'metadata.dfdn.ProductType.untouched',
          'metadata.dfas.RequestorUserId': 'metadata.dfas.RequestorUserId.untouched',
          'metadata.source': 'metadata.source'
          //'metadata.dataset_type': 'metadata.dataset_type'
        },
        enable_rangeselect: true,
        enable_locationselect: true,
        paging: {
          from: 0,
          size: 10
        },
        pager_on_top: true,
        search_sortby: [{ 'display': 'starttime', 'field': 'starttime' },
                        { 'display': 'endtime', 'field': 'endtime' },
                        { 'display': 'timestamp', 'field': '@timestamp' }],
        sort: [{ '_timestamp': { "order": "desc"} }],
        fields: [ '_timestamp', '_source'],
        display_images: false,
        pre_search_callback: function() {
          if (backdrop === null) {
            // fade the backdrop in
            var animate = 'fade';
            var doAnimate = $.support.transition && animate;
            backdrop = $('<div class="loading-backdrop ' + animate + '" />').appendTo(document.body);
            if (doAnimate) backdrop[0].offsetWidth;
            backdrop.addClass('in');
            if (doAnimate) backdrop.one($.support.transition.end, function() {});
          }
        },
        post_search_callback: function() {
          // remove the backdrop
          $(".loading-backdrop").remove();
          backdrop = null;
        },
        grq_results_limit: {{ config['GRQ_RESULTS_LIMIT'] }},
        word_cloud: false,
        result_display: [
          [
            {
              "pre": " <strong>(",
              "field": "dataset",
              "post": ")</strong>"
            },
            {
              "pre": " <strong>",
              "field": "id",
              "post": "</strong><table>"
            }
          ],
          [
            {
              "pre": "<tr><td><div class='hidden'>",
              "field": "id",
              "post": "</div>"
            },
            {
              "pre": "tags: <font color='blue'>", 
              "field": "metadata.tags", 
              "post": "</font>" 
            }
          ],
          [
            {
              "pre": "corrections: <font color='blue'>", 
              "field": "metadata.corrections", 
              "post": "</font>" 
            }
          ],
          [
            {
              "pre": "version: <font color='blue'>", 
              "field": "metadata.version", 
              "post": "</font>" 
            },
          ],
          [
            {
              "pre": "system version: <font color='blue'>", 
              "field": "system_version", 
              "post": "</font>" 
            },
          ],
          [
            {
              "pre": "continent: <font color='blue'>",
              "field": "continent",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "location: <div class='hidden'>",
              "field": "id",
              "post": "</div><font color='blue'>"
            },
            {
              "pre": "",
              "field": "city.admin2_name",
              "post": ", "
            },
            {
              "pre": "",
              "field": "city.admin1_name",
              "post": ", "
            },
            {
              "pre": "",
              "field": "city.country_name",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "cities: <font color='blue'>",
              "field": "city.name",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "sensing start: <font color='blue'>",
              "field": "metadata.sensingStart",
              "post": "</font> | "
            },
            {
              "pre": "sensing stop: <font color='blue'>",
              "field": "metadata.sensingStop",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "spacecraft name: <font color='blue'>",
              "field": "metadata.spacecraftName",
              "post": "</font> | "
            },
            {
              "pre": "track number: <font color='blue'>",
              "field": "metadata.trackNumber",
              "post": "</font> | "
            },
            {
              "pre": "beam number: <font color='blue'>",
              "field": "metadata.beamNumber",
              "post": "</font> | "
            },
/*
            {
              "pre": "lat index min: <font color='blue'>",
              "field": "metadata.latitudeIndexMin",
              "post": "</font> | "
            },
            {
              "pre": "lat index max: <font color='blue'>",
              "field": "metadata.latitudeIndexMax",
              "post": "</font>"
            },
*/
            {
              "pre": "frame ID: <font color='blue'>",
              "field": "metadata.frameID",
              "post": "</font> | "
            }
          ],
          [
            {
              "pre": "orbit direction: <font color='blue'>",
              "field": "metadata.direction",
              "post": "</font> | "
            },
            {
              "pre": "look direction: <font color='blue'>",
              "field": "metadata.lookDirection",
              "post": "</font> | "
            },
            {
              "pre": "orbit number: <font color='blue'>",
              "field": "metadata.orbitNumber",
              "post": "</font> | "
            },
            {
              "pre": "orbit repeat: <font color='blue'>",
              "field": "metadata.orbitRepeat",
              "post": "</font>"
            }
          ],
/*
          [
            {
              "pre": "vertical baseline: <font color='blue'>",
              "field": "metadata.verticalBaseline",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "horizontal baseline: <font color='blue'>",
              "field": "metadata.horizontalBaseline",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "perpendicular baseline: <font color='blue'>",
              "field": "metadata.totalBaseline",
              "post": "</font>"
            }
          ],
*/
          [
            {
              "pre": "reference: <font color='blue'>",
              "field": "metadata.reference",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "Predicted Phase Unwrapping Quality:",
              "field": "metadata.predicted_phase_unwrapping_quality",
              "post": ""
            }
          ],
          //AOIs and event data
          [
            {
              "pre": "Event ID:",
              "field": "eventid",
              "post": ""
            },
            {
              "pre": "Alternative Event IDs:",
              "field": "eventids",
              "post": ""
            },
            {
              "pre": "Event Webpage:",
              "field": "event-webpage",
              "post": ""
            }
          ],
          [
            {
              "pre": "product type: <font color='blue'>",
              "field": "metadata.dfdn.ProductType",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "requestor: <font color='blue'>",
              "field": "metadata.dfas.RequestorUserId",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "bbox: <font color='blue'>",
              "field": "metadata.bbox",
              "post": "</font>"
            }
          ],
          [
            {
              "pre": "user tags:<div id='user_tags_",
              "field": "id",
              "post": "'></div><script>$(function() {\n" +
                      "  var es_index = null;\n" +
                      "  var tagData = null;\n"
            },
            {
              "pre": "  es_index = \"",
              "field": "es_index",
              "post": "\";\n"
            },
            {
              "pre": "  tagData = ",
              "field": "metadata.user_tags",
              "post": ";\n"
            },
            {
              "pre": "  var id='",
              "field": "id",
              "post": "';\n" +
                      "  var tags =  $('div[id=\"user_tags_' + id + '\"]').tags({\n" +
                      "    tagSize: 'sm',\n" +
                      "    tagData: tagData,\n" +
                      "    afterAddingTag: function(t) { add_user_tag(es_index, id, t); },\n" +
                      "    afterDeletingTag: function(t) { remove_user_tag(es_index, id, t); }\n" +
                      "  });\n" +
                      "});<\/script>"
            }
          ],
          [
            {
              "pre": "<span class=\"label label-info\">region</span><div id='map_",
              "field": "id",
              "post": "_"
            },
            {
              "pre": "",
              "field": "system_version",
              "post": "' class=\"map\"></div><br/>"
            },
            {
              "pre": "<button class=\"btn btn-link\" type=\"button\" id='load_browse_",
              "field": "id",
              "post": "_"
            },
            {
              "pre": "",
              "field": "system_version",
              "post": "'>show browse images</button>"
            },
            {
              "pre": "<div id='img_grid_",
              "field": "id",
              "post": "_"
            },
            {
              "pre": "",
              "field": "system_version",
              "post": "'></div><script>$(function() {\n" +
                      "  var imgData = [];\n" +
                      "  var browseUrl = null;\n" +
                      "  var prodUrl = null;\n"
            },
            {
              "pre": "  prodUrl = '",
              "field": "urls",
              "post": "';\n"
            },
            {
              "pre": "  var browseUrl = '",
              "field": "browse_urls",
              "post": "';\n"
            },
            {
              "pre": "  imgData = ",
              "field": "images",
              "post": ";\n"
            },
            {
              "pre": "  var system_version = '",
              "field": "system_version",
              "post": "';\n"
            },
            {
              "pre": "  var id='",
              "field": "id",
              "post": "';\n" +
                      "  var grid = $('div[id=\"img_grid_' + id + '_' + system_version + '\"]');\n" +
                      "  grid.append('<table><tr>');\n" +
                      "  for (var i=0; i<imgData.length; i++) {\n" +
                      "    var img_url = prodUrl + '/' + imgData[i].img;\n" +
                      "    var small_img_url = browseUrl + '/' + imgData[i].small_img;\n" +
                      "    var tooltip = '';\n" +
                      "    if (typeof imgData[i].tooltip == 'string' || imgData[i].tooltip instanceof String) {\n" +
                      "      if (imgData[i].tooltip.length > 0) \n" +
                      "        tooltip = '<span class=\"hidden label label-info\">' + imgData[i].tooltip + '</span>';\n" +
                      "    }\n" +
                      "    grid.append('<td>' + tooltip + '<a target=\"_blank\" href=\"' + img_url + '\">" +
                      "<img data-src=\"' + small_img_url + '\" class=\"lazy-img img-rounded\" width=\"250px\" height=\"250px\" /></a></td>');\n" +
                      "    if (i % 3 == 2) grid.append('</tr><tr>');\n" +
                      "  }\n" +
                      "  grid.append('</tr></table>');\n" +
                      "  grid.hide();\n" +
                      "  var img_ldr = $('button[id=\"load_browse_' + id + '_' + system_version + '\"]');\n" +
                      "  img_ldr.click(function(ev) {\n" +
                      "    ev.preventDefault();\n" +
                      "    grid.show();\n" +
                      "    $(this).closest(\"table\").find(\"img.lazy-img\").imageloader({\n" +
                      "      callback: function(elm) {\n" +
                      "        $(elm).parent(\"a\").parent().find(\"span.label\").removeClass(\"hidden\");\n" +
                      "      }\n" +
                      "    });\n" +
                      "    img_ldr.remove();\n" +
                      "  });\n" +
                      "});<\/script>"
            }
          ],
          [
            {
              "pre": "<script>$(function() { var id = '",
              "field": "id",
              "post": "';\n" +
                      "var tiles = false;\n" +
                      "var tile_layers = [];\n" +
                      "var tile_max_zoom= [];\n" +
                      "var prodUrl = null;\n"
            },
            {
              "pre": " var system_version = '",
              "field": "system_version",
              "post": "';\n" +
                      "  var map = L.map('map_' + id + '_' + system_version," +
                      " {worldCopyJump: true, center: [0,0], zoom: 0, zoomControl: false});\n" +
                      //"L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {\n" +
                      "L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {\n" +
                      "  maxZoom: 18\n" +
                      "}).addTo(map);\n"
            },
            {
              "pre": "var coords = [",
              "field": "location.coordinates",
              "post": "];\n"
            },
            {
              "pre": "var location_type = '",
              "field": "location.type",
              "post": "';\n" +
                      "var geojson = get_geojson(coords, location_type);\n" +
                      "//L.geoJson(geojson).bindPopup(id).addTo(map);\n" +
                      "var link_ds = $('<a class=\"select_dataset\">'+id+'</a>').click(function() {\n" +
                      "  $('.facetview_freetext').val('_id:\"'+id+'\"');\n" +
                      "  $('.facetview_freetext').keyup();\n" +
                      "})[0];\n" +
                      "var geojson_layer = L.geoJson(geojson, {style:{fill:true,fillOpacity:0,weight:1}}).bindPopup(link_ds).addTo(map);\n" +
                      "var geojson_layer_search = L.geoJson(geojson, {style:{fill:true,fillOpacity:0,weight:1}}).bindPopup(link_ds).addTo(prodLayer);\n" +
                      "var min_lon = $('#min_lon').val();\n" +
                      "var max_lon = $('#max_lon').val();\n" +
                      "var min_lat = $('#min_lat').val();\n" +
                      "var max_lat = $('#max_lat').val();\n" +
                      'if (!(min_lon == "-180" && max_lon == "180" && min_lat == "-90" && max_lat == "90")) {\n' +
                      "  var bbox_north = parseFloat(max_lat);\n" +
                      "  var bbox_south = parseFloat(min_lat);\n" +
                      "  var bbox_east = parseFloat(max_lon);\n" +
                      "  var bbox_west = parseFloat(min_lon);\n" +
                      "  L.polygon([\n" +
                      "      [ bbox_south, bbox_west ],\n" +
                      "      [ bbox_north, bbox_west ],\n" +
                      "      [ bbox_north, bbox_east ],\n" +
                      "      [ bbox_south, bbox_east ]\n" +
                      "    ], {\n" +
                      "      stroke: true,\n" +
                      "      color: '#f06eaa',\n" +
                      "      weight: 4,\n" +
                      "      opacity: 0.5,\n" +
                      "      fill: true,\n" +
                      "      fillColor: null, //same as color by default\n" +
                      "      fillOpacity: 0.2,\n" +
                      "      clickable: true\n" +
                      "  }).bindPopup(link_ds).addTo(map);\n" +
                      "}\n"
            },
            {
              "pre": "tiles = ",
              "field": "metadata.tiles",
              "post": ";\n"
            },
            {
              "pre": "tile_layers = ",
              "field": "metadata.tile_layers",
              "post": ";\n"
            },
            {
             "pre": "tile_max_zoom = ",
             "field": "metadata.tile_max_zoom",
             "post": ";\n"
            },
            {
              "pre": "  prodUrl = '",
              "field": "urls",
              "post": "';\n" +
                      'if (tiles) {\n' +
                      "  var res_ds_layers = {};\n" +
                      "  for (var i=0; i < tile_layers.length; i++) {\n" +
                      "    var res_ds_layer = L.tileLayer(prodUrl + '/tiles/{ds}/{z}/{x}/{y}.png', {\n" +
                      "      ds: tile_layers[i],\n" +
                      "      opacity: 1,\n" +
                      "      minZoom: 0,\n" +
                      "      maxZoom: 18,\n" +
                      "      maxNativeZoom: get_tile_max_zoom(tile_max_zoom, i),\n" +
                      "      reuseTiles: true,\n" +
                      "      tms: true,\n" +
                      "      noWrap: true,\n" +
                      "      bounds: geojson_layer.getBounds()\n" +
                      "    }).addTo(map);\n" +
                      "    res_ds_layers[tile_layers[i]] = res_ds_layer;\n" +
                      "    L.tileLayer(prodUrl + '/tiles/{ds}/{z}/{x}/{y}.png', {\n" +
                      "      ds: tile_layers[i],\n" +
                      "      opacity: .6,\n" +
                      "      minZoom: 0,\n" +
                      "      maxZoom: 18,\n" +
                      "      maxNativeZoom: get_tile_max_zoom(tile_max_zoom, i),\n" +
                      "      reuseTiles: true,\n" +
                      "      tms: true,\n" +
                      "      noWrap: true,\n" +
                      "      bounds: geojson_layer.getBounds()\n" +
                      "    }).addTo(prodLayer);\n" +
                      "  }\n" +
                      "  L.control.layers(res_ds_layers).addTo(map);\n" +
                      "}\n"
            },
            {
              "pre": "var center = [",
              "field": "metadata.center.coordinates",
              "post": "];\n" +
                     "map.setView([center[1], center[0]], 7);\n" +
                     "location_search_map.setView([center[1], center[0]+3], 7);\n" +
                      "});\n" +
                      "<\/script>"
            }
          ],
          [
            {
              "pre": '<table><tr><td><a class="btn btn-success" target="_blank" href="',
              "field": "urls",
              "post": '">Browse</a></td>'
            },
            {
              "pre": '<td id="searchprov_',
              "field": "id",
              "post": '"><a class="btn btn-info" target="_blank">Provenance</a>'
            },
            {
              "pre": "</div><script>$(function() {\n" +
                     '  var id = "', 
              "field": "id",
              "post": '";\n' +
                     "  var link = $(jq('searchprov_' + id + ' a'));\n" +
                     'link.attr("href", \'{{ config['PROVES_URL'] }}/?source={"query":{"bool":{"must":[{"term":{"prov:type.raw":"eos:product"}},{"query_string":{"query":"\\\\"\' + id + \'\\\\""}}]}}}\');\n' +
                      "});<\/script></td>"
            },
            {
              "pre": '<td id="queryregion_',
              "field": "id",
              "post": '"><a class="btn" target="_blank">Query Region</a>'
            },
            {
              "pre": "</div><script>$(function() {\n" +
                     '  var id = "', 
              "field": "id",
              "post": '";\n' +
                     "  var link = $(jq('queryregion_' + id + ' a'));\n"
            },
            {
              "pre": "  var coords = [",
              "field": "location.coordinates",
              "post": "];\n"
            },
            {
              "pre": "  var location_type = '",
              "field": "location.type",
              "post": "';\n" +
                      "  var geojson = get_geojson(coords, location_type);\n" +
                      '  link.on("click", function() {\n' +
                      "    drawnItems.clearLayers();\n" +
                      "    L.geoJson(geojson, {\n" +
                      "        stroke: true,\n" +
                      "        color: '#f06eaa',\n" +
                      "        weight: 4,\n" +
                      "        opacity: 0.5,\n" +
                      "        fill: true,\n" +
                      "        fillColor: null, //same as color by default\n" +
                      "        fillOpacity: 0.2,\n" +
                      "        clickable: true\n" +
                      "    }).bindPopup('search bbox').addTo(drawnItems);\n" +
                      "    var bnds = extractLatLonValues(drawnItems.getBounds());\n" +
                      "    var bbox_north = bnds[0];\n" +
                      "    var bbox_south = bnds[1];\n" +
                      "    var bbox_west = bnds[2];\n" +
                      "    var bbox_east = bnds[3];\n" +
                      "    drawnItems.clearLayers();\n" +
                      "    L.polygon([\n" +
                      "        [ bbox_south, bbox_west ],\n" +
                      "        [ bbox_north, bbox_west ],\n" +
                      "        [ bbox_north, bbox_east ],\n" +
                      "        [ bbox_south, bbox_east ]\n" +
                      "      ], {\n" +
                      "        stroke: true,\n" +
                      "        color: '#f06eaa',\n" +
                      "        weight: 4,\n" +
                      "        opacity: 0.5,\n" +
                      "        fill: true,\n" +
                      "        fillColor: null, //same as color by default\n" +
                      "        fillOpacity: 0.2,\n" +
                      "        clickable: true\n" +
                      "    }).addTo(drawnItems);\n" +
                      "    updateLatLonValues(drawnItems.getBounds());\n" +
                      "    location_search_map.fitBounds(drawnItems.getBounds());\n" +
                      '  });\n' +
                      "});<\/script>"
            },
            {
              "pre": '<td><a class="btn" target="_blank" href="',
              "field": "visualization-url",
              "post": '">Visualize</a></td>'
            },
            {
              "pre": ' <div class="hidden" id="hidden_id_',
              "field": "id",
              "post": '"/></td></tr></table>'
            }
          ]
        ]
      });
    
      // init range_slider_start
      /*
      $( "#range_slider_starttime" ).dateRangeSlider({
        bounds: {
          min: new Date(2000, 0, 1),
          max: new Date()
        },
        defaultValues: {
          min: new Date(2000, 0, 1),
          max: new Date()
        } 
      }); 
      */

      // set tablecloth
      var rules_table = $('#rules_table').tablecloth({
        theme: "stats",
        striped: true,
        condensed: true
      });

      // validate form
      var validator = $( '#rule_form' ).validate({
        rules: {
          rule_name: {
            required: true
          },
          query_string: {
            required: true
          },
          workflow: {
            minlength: 1,
            required: true
          },
          priority: {
            minlength: 1,
            required: true
          }
        },
        messages: {
          rule_name: "Please specify a name for this rule.",
          workflow: "Please select an action.",
          priority: "Please select a priority."
        }
      });

      // validate procthis form
      var procthis_validator = $( '#procthis_form' ).validate({
        rules: {
          procthis_name: {
            required: true
          },
          query_string: {
            required: true
          },
          workflow: {
            minlength: 1,
            required: true
          },
          priority: {
            minlength: 1,
            required: true
          }
        },
        messages: {
          procthis_name: "Please specify a tag for this job.",
          workflow: "Please select an action.",
          priority: "Please select a priority."
        }
      });

      // show rules modal
      $('#my_rules').on('click', function() {
        $.ajax({
          url: "user_rules/list",
          success: function(data, sts, xhr) {
            //console.log(data);
            $('#general_error').html("");

            // clear table
            var tbody = $('#rules_table > tbody'); 
            tbody.empty();

            // populate table
            for (var i=0; i < data.rules.length; i++) {
              var status_cell = "<td><button class='btn btn-mini btn-danger toggle_rule' type='button' value='" +
                                data.rules[i]['id'] + "'>Off</button></td>";
              if (data.rules[i]['enabled'])
                status_cell = "<td><button class='btn btn-mini btn-success toggle_rule' type='button' value='" +
                              data.rules[i]['id'] + "'>On</button></td>";
              tbody.append("<tr id='rule_" + data.rules[i]['id'] + "'>" +
                           "<td>" + data.rules[i]['rule_name'] + "</td>" +
                           "<td>" + data.rules[i]['query_string'] + "</td>" +
                           "<td>" + data.rules[i]['workflow'] + "</td>" +
                           "<td>" + data.rules[i]['priority'] + "</td>" +
                           "<td>" + data.rules[i]['kwargs'] + "</td>" +
            {% if g.user.id == config['OPS_USER'] %}
                           "<td>" + data.rules[i]['username'] + "</td>" +
            {% endif %}
                           status_cell +
                           "<td><button class='btn btn-mini btn-primary edit_rule' type='button' value='" + 
                           data.rules[i]['id'] + "'>Edit</button></td>" +
                           "<td><button class='btn btn-mini btn-warning remove_rule' type='button' value='" + 
                           data.rules[i]['id'] + "' rule_name='" + data.rules[i]['rule_name'] + 
                           "'>Delete</button></td></tr>");
            }

            // append handlers to status buttons
            $('button.toggle_rule').on('click', function() {
              var button = $(this);
              var rule_id = button.attr('value');
              var cur_status = button.text();
              if (cur_status == "Off") {
                var new_status_text = "On";
                var new_status = "true";
                var remove_class = "btn-danger";
                var add_class = "btn-success";
              }else {
                var new_status_text = "Off";
                var new_status = "false";
                var remove_class = "btn-success";
                var add_class = "btn-danger";
              }
              $.ajax({
                type: "POST",
                url: "user_rules/toggle_status",
                data: {
                  id: rule_id,
                  enabled: new_status
                },
                success: function(data, sts, xhr) {
                  button.toggleClass(remove_class + " " + add_class).text(new_status_text);
                },
                error: function(xhr, sts, err) {
                  $('#general_error').html("Error: " + xhr.responseText);
                  $('#error_modal').modal('show').css({'left': set_left_margin});
                }
              });
            });

            // append handlers to delete buttons
            $('button.remove_rule').on('click', function() {
              var rule_id = $(this).attr('value');
              var rule_name = $(this).attr('rule_name');
              $('#delete_rule_name').text(rule_name);
              $('#delete_rule_id').val(rule_id);
              $('#confirm_delete_modal').modal('show').css({'left': set_left_margin});
            });

            // append handlers to edit buttons
            $('button.edit_rule').on('click', function() {
              var parent_tr = $(this).closest('tr');
              var rule_id = $(this).attr('value');
              $('#rule_id').val(rule_id);
              $('#rule_name').val(parent_tr.children().eq(2).text());
              $('#query_string').val(parent_tr.children().eq(3).text());
              $('#workflow_val').val(parent_tr.children().eq(4).text());
              $('#priority_val').val(parent_tr.children().eq(5).text());
              $('#kwargs').val(parent_tr.children().eq(6).text());
              $('#rule_modal_label').text("Edit Rule");
              $('#rule_modal').modal('show').css({'left': set_left_margin});
              $('#list_rules_modal').modal('hide');
            });
            /* // Export Rules Button setup
            $('button.user-rules-export').on('click', function() {
              $.ajax({
                 url: "user_rules/list",
                 success: function(data, sts, xhr) {
                   var tmp = $("#user-rules-download");
                   var dta = JSON.stringify(data).replace("\\n","\n");
                   
                   tmp.val(dta);
                   $('#export_rules_modal').modal('show').css({'left': set_left_margin});
                   $('#list_rules_modal').modal('hide');
                 }
              });
            });
            //Import Rules Button Setup
            $('button.user-rules-import').on('click', function() {
                 $('#import_rules_modal').modal('show').css({'left': set_left_margin});
                 $('#list_rules_modal').modal('hide');
                 $('button.import_list_rules').on('click', function() {
                         var text = $("#user-rules-upload").val();
                         text = text.replace(/(\r\n|\n|\r)/gm,"");
                         var data = JSON.parse(text);
                         for (var i = 0; i < data.rules.length; i++)
                         {
                            var update_url = "user_rules/add";
                            $.ajax({
                              type: "POST",
                              url: update_url,
                              data: data.rules[i],
                              success: function(data, sts, xhr) {
                                //console.log(data);
                                $('#ajax_error').html("");
                                $('#rule_modal').modal('hide');
                              },
                              error: function(xhr, sts, err) {
                                //console.log(xhr);
                                var resp = JSON.parse(xhr.responseText);
                                $('#ajax_error').html("Error: " + resp.message);
                              }
                            }); 
                         }
                     });
            });
            //Add rules
            $('button.user-rules-add').on('click', function() {
              $('#rule_id').val("");
              $('#rule_name').val("");
              $('#query_string').val("{}");
              $('#workflow_val').val("");
              $('#priority_val').val(0);
              $('#kwargs').val("");
              $('#rule_modal_label').text("Add Rule");
              $('#rule_modal').modal('show').css({'left': set_left_margin});
              $('#list_rules_modal').modal('hide');
            });
 

            // show modal
            */

            // show modal
            $('#list_rules_modal').modal('show').css({'left': set_left_margin});
          },
          error: function(xhr, sts, err) {
            //console.log(xhr);
            $('#general_error').html("Error: " + xhr.responseText);
            $('#error_modal').modal('show').css({'left': set_left_margin});
          }
        });
        return false;
      });

      // handler for confirm_delete_btn
      $('#confirm_delete_btn').on('click', function() {
        var rule_id = $('#delete_rule_id').val();
        $.ajax({
          type: "POST",
          url: "user_rules/remove",
          data: {
            id: rule_id
          },
          success: function(data, sts, xhr) {
            $('#rule_' + rule_id).remove();
            $('#confirm_delete_modal').modal('hide');
            $('#general_error').html("");
          },
          error: function(xhr, sts, err) {
            $('#confirm_delete_modal').modal('hide');
            $('#general_error').html("Error: " + xhr.responseText);
            $('#error_modal').modal('show').css({'left': set_left_margin});
          }
        });
      });

      // handler for rule_modal
      $('#rule_modal').on('show', function() {
        $('#ajax_error').html("");
        var rule_id = $('#rule_id').val();

        // check if we're in add mode
        if (rule_id === "") {
          var edit_mode = false;
          var cur_kwargs = {};

          // reset everything
          $('#dynamic_fields').empty();
          validator.resetForm();

          // populate query_string
          var query_json = JSON.stringify(JSON.parse(QUERY_STRING).query, null, '  ');
          $('#query_string').val(query_json);
          //$('#query_string').val(query_json).attr('disabled', true);
        }else {
          var edit_mode = true;
          var cur_kwargs = JSON.parse($('#kwargs').val());
        }
        //console.log("workflow_val: " + $('#workflow_val').val());
        //console.log("priority_val: " + $('#priority_val').val());
        //console.log("kwargs: " + $('#kwargs').val());

        // get actions config
        $.ajax({
          url: "user_rules/actions_config?ifc=monitor",
          success: function(data, sts, xhr) {
            //console.log(data);
            // populate workflow/action select options
            var workflow = $('#workflow');
            workflow.empty();
            workflow.append("<option value=''></option>");
            var actions_cfg = {};
            for (var i=0; i < data.actions.length; i++) {
              actions_cfg[data.actions[i].type] = data.actions[i];
              var disabled = data.actions[i].public ? ">" : "disabled>";
              workflow.append("<option value='" + data.actions[i].type + "' " +
                              disabled + data.actions[i].label + "</option>");
            }

            // add handler to build dynamic form on selected option
            workflow.change(function() {
              // build dynamic form
              var workflow_type = $(this).val();
              var dyn_fields = $('#dynamic_fields');
              dyn_fields.empty();
              var kwargs = actions_cfg[workflow_type].kwargs;
              if (kwargs.length > 0)
                dyn_fields.append("<legend>" + workflow_type + " parameters</legend>");
              var field_groups = {};
              for (var i=0; i < kwargs.length; i++) {
                var kwarg = kwargs[i];
                if (kwarg.group !== undefined && !(kwarg.group in field_groups)) {
                  dyn_fields.append("<legend><font color='blue'>" + kwarg.group + "</font></legend>");
                  field_groups[kwarg.group] = true;
                }
                if (kwarg.type == "textbox") {
                  var span_size = "span4";
                  if ("span_size" in kwarg) span_size = kwarg.span_size;
                  var default_value = "";
                  if ("default_value" in kwarg) default_value = kwarg.default_value;
                  dyn_fields.append("<div class='control-group'>" +
                                    "<label class='control-label' for='" + 
                                    kwarg.name + "'>" + kwarg.name + "</label>" +
                                    "<div class='controls'>" +
                                    "<input class='field " + span_size + "' type='text' name='" + kwarg.name +
                                    "' placeholder='" + kwarg.placeholder + "' value='" + default_value + "'></div></div>");
                  $('#rule_form input[name=' + kwarg.name + ']').rules("remove");
                  $('#rule_form input[name=' + kwarg.name + ']').rules("add", kwarg.validator);
                  if (kwarg.name in cur_kwargs)
                    $('#dynamic_fields input[name=' + kwarg.name + ']').val(cur_kwargs[kwarg.name]);
                }else if (kwarg.type == "textarea") {
                  var span_size = "span4";
                  if ("span_size" in kwarg) span_size = kwarg.span_size;
                  var rows = 5;
                  if ("rows" in kwarg) rows = kwarg.rows;
                  var default_value = "";
                  if ("default_value" in kwarg) default_value = kwarg.default_value;
                  dyn_fields.append("<div class='control-group'>" +
                                    "<label class='control-label' for='" + 
                                    kwarg.name + "'>" + kwarg.name + "</label>" +
                                    "<div class='controls'>" +
                                    "<textarea class='field " + span_size + "' type='textarea' rows='" + rows + "' name='" + kwarg.name +
                                    "' placeholder='" + kwarg.placeholder + "'>" + default_value + "</textarea></div></div>");
                  $('#rule_form textarea[name=' + kwarg.name + ']').rules("remove");
                  $('#rule_form textarea[name=' + kwarg.name + ']').rules("add", kwarg.validator);
                  if (kwarg.name in cur_kwargs)
                    $('#dynamic_fields textarea[name=' + kwarg.name + ']').val(cur_kwargs[kwarg.name]);
                }else {
                }
              }
            });

            // select the current workflow and priority
            if (edit_mode) {
              $('#workflow').val($('#workflow_val').val()).change();
              $('#priority').val($('#priority_val').val()).change();
            }
          },
          error: function(xhr, sts, err) {
            //console.log(xhr.responseData);
            $('#general_error').html("Error: " + xhr.responseText);
            $('#error_modal').modal('show').css({'left': set_left_margin});
          }
        });
      });

      $('#rule_modal').on('hide', function() {
        $('#rule_id').val("");
        $('#workflow_val').val("");
        $('#priority_val').val("");
        $('#kwargs').val("");
      });

      // handler for rule button
      $('#rule_btn').on('click', function() {
        var rule_id = $('#rule_id').val();

        // check if we're in add mode
        if (rule_id === "") var edit_mode = false;
        else var edit_mode = true;

        if ($('#rule_form').valid()) {
          //console.log("workflow: " + $('#workflow').val());
          //console.log("priority: " + $('#priority').val());
          //console.log("rule_name: " + $('#rule_name').val());
          //console.log("query_string: " + $('#query_string').val());
          df_fields = {};
          $.each($('#dynamic_fields').find('.field'), function(idx, value) {
            var dyn_input = $(value);
            df_fields[dyn_input.attr('name')] = dyn_input.val();
          });

          if (edit_mode) {
            var rule_data = {
              id: rule_id,
              rule_name: $('#rule_name').val(),
              workflow: $('#workflow').val(),
              priority: $('#priority').val(),
              query_string: $('#query_string').val(),
              kwargs: JSON.stringify(df_fields, null, '  ')
            };
            var update_url = "user_rules/edit";
          }else {
            var rule_data = {
              rule_name: $('#rule_name').val(),
              workflow: $('#workflow').val(),
              priority: $('#priority').val(),
              query_string: $('#query_string').val(),
              kwargs: JSON.stringify(df_fields, null, '  ')
            };
            var update_url = "user_rules/add";
          }
          $.ajax({
            type: "POST",
            url: update_url,
            data: rule_data,
            success: function(data, sts, xhr) {
              //console.log(data);
              $('#ajax_error').html("");
              $('#rule_modal').modal('hide');
            },
            error: function(xhr, sts, err) {
              //console.log(xhr);
              var resp = JSON.parse(xhr.responseText);
              $('#ajax_error').html("Error: " + resp.message);
            }
          });
        }
      });

      // handler for procthis_modal
      $('#procthis_modal').on('show', function() {

        var cur_kwargs = {};

        // reset everything
        $('#procthis_dynamic_fields').empty();
        procthis_validator.resetForm();

        // populate query_string
        var query_json = JSON.stringify(JSON.parse(QUERY_STRING).query, null, '  ');
        $('#procthis_query_string').val(query_json);
        //$('#procthis_query_string').val(query_json).attr('disabled', true);
        //console.log("workflow_val: " + $('#procthis_workflow_val').val());
        //console.log("priority_val: " + $('#procthis_priority_val').val());
        //console.log("kwargs: " + $('#procthis_kwargs').val());

        // get actions config
        $.ajax({
          url: "user_rules/actions_config?ifc=process",
          success: function(data, sts, xhr) {
            //console.log(data);
            // populate workflow/action select options
            var workflow = $('#procthis_workflow');
            workflow.empty();
            workflow.append("<option value=''></option>");
            var actions_cfg = {};
            for (var i=0; i < data.actions.length; i++) {
              actions_cfg[data.actions[i].type] = data.actions[i];
              var disabled = data.actions[i].public ? ">" : "disabled>";
              workflow.append("<option value='" + data.actions[i].type + "' " +
                              disabled + data.actions[i].label + "</option>");
            }

            // add handler to build dynamic form on selected option
            workflow.change(function() {
              // build dynamic form
              var workflow_type = $(this).val();
              var dyn_fields = $('#procthis_dynamic_fields');
              dyn_fields.empty();
              var kwargs = actions_cfg[workflow_type].kwargs;
              if (kwargs.length > 0)
                dyn_fields.append("<legend>" + workflow_type + " parameters</legend>");
              var field_groups = {};
              for (var i=0; i < kwargs.length; i++) {
                var kwarg = kwargs[i];
                if (kwarg.group !== undefined && !(kwarg.group in field_groups)) {
                  dyn_fields.append("<legend><font color='blue'>" + kwarg.group + "</font></legend>");
                  field_groups[kwarg.group] = true;
                }
                if (kwarg.type == "textbox") {
                  var span_size = "span4";
                  if ("span_size" in kwarg) span_size = kwarg.span_size;
                  var default_value = "";
                  if ("default_value" in kwarg) default_value = kwarg.default_value;
                  dyn_fields.append("<div class='control-group'>" +
                                    "<label class='control-label' for='" + 
                                    kwarg.name + "'>" + kwarg.name + "</label>" +
                                    "<div class='controls'>" +
                                    "<input class='field " + span_size + "' type='text' name='" + kwarg.name +
                                    "' placeholder='" + kwarg.placeholder + "' value='" + default_value + "'></div></div>");
                  $('#procthis_form input[name=' + kwarg.name + ']').rules("remove");
                  $('#procthis_form input[name=' + kwarg.name + ']').rules("add", kwarg.validator);
                  if (kwarg.name in cur_kwargs)
                    $('#procthis_dynamic_fields input[name=' + kwarg.name + ']').val(cur_kwargs[kwarg.name]);
                }else if (kwarg.type == "textarea") {
                  var span_size = "span4";
                  if ("span_size" in kwarg) span_size = kwarg.span_size;
                  var rows = 5;
                  if ("rows" in kwarg) rows = kwarg.rows;
                  var default_value = "";
                  if ("default_value" in kwarg) default_value = kwarg.default_value;
                  dyn_fields.append("<div class='control-group'>" +
                                    "<label class='control-label' for='" + 
                                    kwarg.name + "'>" + kwarg.name + "</label>" +
                                    "<div class='controls'>" +
                                    "<textarea class='field " + span_size + "' type='textarea' rows='" + rows + "' name='" + kwarg.name +
                                    "' placeholder='" + kwarg.placeholder + "'>" + default_value + "</textarea></div></div>");
                  $('#procthis_form textarea[name=' + kwarg.name + ']').rules("remove");
                  $('#procthis_form textarea[name=' + kwarg.name + ']').rules("add", kwarg.validator);
                  if (kwarg.name in cur_kwargs)
                    $('#procthis_dynamic_fields textarea[name=' + kwarg.name + ']').val(cur_kwargs[kwarg.name]);
                }else {
                }
              }
            });
          },
          error: function(xhr, sts, err) {
            //console.log(xhr.responseData);
            $('#general_error').html("Error: " + xhr.responseText);
            $('#error_modal').modal('show').css({'left': set_left_margin});
          }
        });
      });

      // handler for procthis button
      $('#procthis_btn').on('click', function() {
        if ($('#procthis_form').valid()) {
          //console.log("workflow: " + $('#procthis_workflow').val());
          //console.log("priority: " + $('#procthis_priority').val());
          //console.log("procthis_name: " + $('#procthis_name').val());
          //console.log("query_string: " + $('#procthis_query_string').val());
          df_fields = {};
          $.each($('#procthis_dynamic_fields').find('.field'), function(idx, value) {
            var dyn_input = $(value);
            df_fields[dyn_input.attr('name')] = dyn_input.val();
          });

          var procthis_data = {
            name: $('#procthis_name').val(),
            workflow: $('#procthis_workflow').val(),
            priority: $('#procthis_priority').val(),
            query_string: $('#procthis_query_string').val(),
            kwargs: JSON.stringify(df_fields, null, '  ')
          };

          $('#procthis_modal').modal('hide');
          $('#result_modal').modal('show').css({'left': set_left_margin});

          var submit_url = "user_rules/submit_job";
          $.ajax({
            type: "POST",
            url: submit_url,
            data: procthis_data,
            success: function(data, sts, xhr) {
              //console.log(data);
              $('#result_modal .modal-body-div').html(data.html);
            },
            error: function(xhr, sts, err) {
              //console.log(xhr);
              $('#result_modal .modal-body-div').html("");
              try {
                var resp = JSON.parse(xhr.responseText);
                $('#procthis_ajax_error').html("Error: " + resp.message);
              } catch(jerr) {
                $('#procthis_ajax_error').html("Error: " + err);
              }
            }
          });
        }
      });

      // handler for result_modal
      $('#result_modal').on('show', function() {
        $('#procthis_ajax_error').html("");
        $('#result_modal .modal-body-div').html(
          "<p>Processing...</p>" +
          "<div class=\"text-center\">" +
          "<img src=\"{{ url_for('static', filename='preloaders/square/128x128/Preloader_5/Preloader_5.gif') }}\"/>" +
          "</div>");
      });

      // show terms of use modal
      $('#tou_link').on('click', function() {
        $('#tou_modal').modal('show').css({'left': set_left_margin});
        return false;
      });

      // open up all facets on page load
      $('.facetview_filtershow').each(function(index, value) {
        var open_facets = [
          'dataset',
          'metadata_platform',
          'metadata_sensor_untouched',
          'system_version',
          'metadata_user_tags_untouched',
          'metadata_tags_untouched',
          'continent_untouched',
          'city_country_name_untouched',
          'city_admin1_name_untouched',
          'city_admin2_name_untouched'
        ];
        if ($.inArray($(value).attr('rel'), open_facets) != -1) $(value).click();
      });
      
      var sI = setInterval(function(){
        //wait for it to be there...
        //arrite lets fork some left browse options...
        //console.log('menu is',$(_this.attr.config.menuSelector).length)
        if($(_this.attr.config.menuSelector).length > 0){
          if($('.facetview_filters').eq(0).find('tr').length > 1){
            //hacky but not sure what's standard
            setTimeout(function(){
              var c = $(_this.attr.config.menuSelector).clone(true);//makes a deep copy with events/data/etc preserved...
              var config = _this.attr.config;
              config.filterDOMObject = c;
              FacetViewMenu.attachTo(document,{config:config});//take our existing global configs, then attach our clone to it.
              
            },100);
            clearInterval(sI);
          }
        }
      },100);
    };
    
    this.injectCSS = function(){
      //inject our CSS into the app, cleaner than making dev's copy/paste a bunch of XML
      var cacheFlag = '?cache='+new Date();//set this to an empty string if you dont want the CSS to cahce during dev...
      var css = this.attr.config.css;
      $.each(css,function(i,url){
        var link = document.createElement("link");
        link.type = "text/css";
        link.rel = "stylesheet";
        link.href = url+cacheFlag;
        document.getElementsByTagName("head")[0].appendChild(link);
      });
    };
  }
});
