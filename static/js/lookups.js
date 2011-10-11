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


var previous = {}, incr = 0;  // global

function update() {
  function incr_number(key, num) {
    var before = $(key).text();
    if (before !== '' + num) {
      // there's a change!
      $(key).fadeTo(200, 0., function() {
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
