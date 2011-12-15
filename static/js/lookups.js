function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

function compareAssociativeArrays(a, b) {
    function nrKeys(a) {
        var i = 0;
        for (key in a) {
            i++;
        }
        return i;
   }
   if (a == b) {
       return true;
   }
   if (nrKeys(a) != nrKeys(b)) {
       return false;
   }
   for (key in a) {
     if (a[key] != b[key]) {
         return false;
     }
   }
   return true;
}

function tsep(n,swap) {
  var ts=",", ds="."; // thousands and decimal separators
  if (swap) { ts=","; ts="."; } // swap if requested

  var ns = String(n),ps=ns,ss=""; // numString, prefixString, suffixString
  var i = ns.indexOf(".");
  if (i!=-1) { // if ".", then split:
    ps = ns.substring(0,i);
    ss = ds+ns.substring(i+1);
  }
  return ps.replace(/(\d)(?=(\d{3})+([.]|$))/g,"$1"+ts)+ss;
}


// globals
var previous = {}
, incr = 0
, chart_jsons = null
, chart_jsonps = null
, chart_usernames = null
, chart_auths = null
;

function cloneObject(source) {
  for (i in source) {
    if (typeof source[i] == 'source') {
      this[i] = new cloneObject(source[i]);
    }
    else{
      this[i] = source[i];
    }
  }
}
function _set_up_charts(numbers) {
  var options = {
     curveType: 'function',
     legend: 'none',
     width:400,
     height:300,
     lineWidth:3
  };
  if (chart_jsons === null && numbers.lookups_json) {
    var p = new cloneObject(options);
    p.title = 'Twitter requests by JSON';
    chart_jsons = new Chart('chart-jsons', p);
  }
  if (chart_jsonps === null && numbers.lookups_jsonp) {
    var p = new cloneObject(options);
    p.title = 'Twitter requests by JSONP';
    chart_jsonps = new Chart('chart-jsonps', p);
  }
  if (chart_usernames === null && numbers.lookups_usernames) {
    var p = new cloneObject(options);
    p.title = 'Total number of usernames looked up';
    p.series = [{color: 'green'}];
    chart_usernames = new Chart('chart-usernames', p);
  }
  if (chart_auths === null && numbers.auths) {
    var p = new cloneObject(options);
    p.title = 'Authentications';
    p.series = [{color: 'red'}];
    chart_auths = new Chart('chart-auths', p);
  }

  if (numbers.lookups_json)
    chart_jsons.add_value(numbers.lookups_json);
  if (numbers.lookups_jsonp)
    chart_jsonps.add_value(numbers.lookups_jsonp);
  if (numbers.lookups_usernames)
    chart_usernames.add_value(numbers.lookups_usernames);
  if (numbers.auths)
    chart_auths.add_value(numbers.auths);

}

function incr_number(key, num) {
  var before = $(key).text();
  if (before !== '' + tsep(num)) {
    // there's a change!
    $(key).fadeTo(200, 0.1, function() {
      $(this).text(tsep(num)).fadeTo(300, 1.0);
    });
  }
}

function process_response(response) {
  if (response.lookups_json && response.lookups_jsonp)
    incr_number('#lookups-total', response.lookups_json + response.lookups_jsonp);
  if (response.lookups_json)
    incr_number('#lookups-json', response.lookups_json);
  if (response.lookups_jsonp)
    incr_number('#lookups-jsonp', response.lookups_jsonp);
  if (response.lookups_usernames)
    incr_number('#lookups-usernames', response.lookups_usernames);
  if (response.auths)
    incr_number('#auths', response.auths);
  _set_up_charts(response);
}

/*
function update() {
  $.getJSON(JSON_URL, function(response) {
    process_response(response);
    var change = !compareAssociativeArrays(response, previous);
    previous = response;

    var t;
    if (change) {
      t = 1;
      incr = 0;
      _set_up_charts(response);
    } else {
      t = Math.min(3 + incr, 10);
      incr += 0.1;
    }
    setTimeout(update, Math.ceil(t * 1000));
  });
}
*/

window.WEB_SOCKET_DEBUG = true;
function setupSocket() {
  var socket = new io.connect('http://' + window.location.host, {
     port: 8888
  });

  socket.on('connect', function() {
    socket.on('message', function(msg) {
      process_response(msg);
    });

  });
}

$(function() {
  setupSocket();
});
