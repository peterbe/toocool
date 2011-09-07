function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

var Lookup = (function() {
  var BASE_URL = 'http://toocoolfor.me';
  //var BASE_URL = 'http://toocool';
  var your_screen_name;
  var _default_interval = 3, _interval = _default_interval;

  var screennames = [];
  var known = {};
  function findScreenNames() {
    var new_screennames = [];
    $('a.tweet-screen-name').each(function(i, e) {
      var v = $.trim($(this).text());
      if (v && $.inArray(v, screennames) == -1) {
        screennames.push(v);
        new_screennames.push(v);
      }
    });
    return new_screennames;
  }

  return {
     callback: function(response) {
         if (response.ERROR) {
           alert(response.ERROR);
           return;
         }
         var screen_name, tag, prefix;

         $('div.tweet-content').each(function() {
           // only display results once
           if ($('a.followsyou,a.followsyounot', this).size())
             return;

           screen_name = $('a.tweet-screen-name', this).text();
           // or if it's you
           if (screen_name == your_screen_name)
             return;

           var result = known[screen_name];
           if (result === undefined) {
             result = response[screen_name];
             known[screen_name] = result;
           }

           if (result) {
             tag = $('<a>', {text: 'follows me'})
               .addClass('followsyou')
                 .css('color', 'green');
           } else {
             tag = $('<a>', {text: 'too cool for me'})
               .addClass('followsyounot')
                 .css('color', '#333');
           }
           tag
             .attr('href', BASE_URL + '/following/' + screen_name)
               .attr('target', '_blank')
                 .attr('title', 'According to follows.me')
                   .css('float', 'right')
                     .css('padding-right', '30px')
                       .css('font-size', '11px')
                         .appendTo($('span.tweet-user-name', this));

         });

     },
     search: function() {
       setTimeout(function() {
         Lookup.search();
       }, _interval * 1000);

       your_screen_name = $.trim($('#screen-name').text());
       var names = findScreenNames();
       names = $.grep(names, function(e) {
         return known[e] === undefined && e != your_screen_name;
       });

       if (!names.length) {
         _interval++;  // nothing has changed
         return;
       }
       _interval = _default_interval;
       var data = {
         you: your_screen_name,
         usernames: names.join(',')
       };
       var s = document.createElement('script');
       s.type = 'text/javascript';
       s.defer = true;
       var url = BASE_URL + '/jsonp?callback=Lookup.callback'
                 + '&usernames=' + data.usernames
                 + '&you=' + data.you;
       s.src = url;
       document.getElementsByTagName('head')[0].appendChild(s);
     }
  }
})();


(function() {
  Lookup.search();
})();
