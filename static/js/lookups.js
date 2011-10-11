
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
  $.getJSON(JSON_URL, function(response) {
    $('#lookups-total').text(response.lookups_json + response.lookups_jsonp);
    $('#lookups-json').text(response.lookups_json);
    $('#lookups-jsonp').text(response.lookups_jsonp);
    $('#lookups-usernames').text(response.lookups_usernames);
    $('#auths').text(response.auths);
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
    console.log(Math.ceil(t*1000));
    setTimeout(update, Math.ceil(t * 1000));
  });
}
$(function() {
  setTimeout(update, 5 * 1000);
});
