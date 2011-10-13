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
  if (chart_jsons === null) {
    var p = new cloneObject(options);
    p.title = 'Twitter requests by JSON';
    chart_jsons = new Chart('chart-jsons', p);
  }
  if (chart_jsonps === null) {
    var p = new cloneObject(options);
    p.title = 'Twitter requests by JSONP';
    chart_jsonps = new Chart('chart-jsonps', p);
  }
  if (chart_usernames === null) {
    var p = new cloneObject(options);
    p.title = 'Total number of usernames looked up';
    p.series = [{color: 'green'}];
    chart_usernames = new Chart('chart-usernames', p);
  }
  if (chart_auths === null) {
    var p = new cloneObject(options);
    p.title = 'Authentications';
    p.series = [{color: 'red'}];
    chart_auths = new Chart('chart-auths', p);
  }

  chart_jsons.add_value(numbers.lookups_json);
  chart_jsonps.add_value(numbers.lookups_jsonp);
  chart_usernames.add_value(numbers.lookups_usernames);
  chart_auths.add_value(numbers.auths);

}

function update() {
  function incr_number(key, num) {
    var before = $(key).text();
    if (before !== '' + num) {
      // there's a change!
      $(key).fadeTo(200, 0.1, function() {
        $(this).text(num).fadeTo(300, 1.0);
      });
    }
  }

  $.getJSON(JSON_URL, function(response) {
    incr_number('#lookups-total', response.lookups_json + response.lookups_jsonp);
    incr_number('#lookups-json', response.lookups_json);
    incr_number('#lookups-jsonp', response.lookups_jsonp);
    incr_number('#lookups-usernames', response.lookups_usernames);
    incr_number('#auths', response.auths);
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

$(function() {
  setTimeout(update, 5 * 1000);
});
