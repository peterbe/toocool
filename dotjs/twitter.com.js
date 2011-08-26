/* Version 0.1
 * 26 August 2011
 *
 * Copyright http://toocoolfor.me
 */


function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

var Lookup = (function() {
  var BASE_URL = 'http://toocoolfor.me';

  var screennames = [];
  function findScreenNames() {
    var new_screennames = [];
    $('a.tweet-screen-name').each(function(i, e) {
      var v = $.trim($(this).text());
      if (v && $.inArray(e, screennames) == -1) {
        screennames.push(v);
        new_screennames.push(v);
      }
    });
    return new_screennames;
  }
  return {
     search: function () {
       var names = findScreenNames();
       var your_screen_name = $.trim($('#screen-name').text());
       var data = {
         you: your_screen_name,
         usernames: names.join(',')
       };
       $.getJSON(BASE_URL + '/json', data, function (response) {
         if (response.ERROR) {
           alert(response.ERROR);
           return;
         }
         var screen_name, tag;

         $('div.tweet-content').each(function() {
           // if it's got one of those 'retweeted by <someoneyoufollow>'
           // then just skip
           if ($('.retweet-icon', this).size())
             return;
           screen_name = $('a.tweet-screen-name', this).text();
           // or if it's you
           if (screen_name == your_screen_name)
             return;

           if (response[screen_name]) {
             tag = $('<a>', {text: 'follows me'})
               .addClass('followsyou')
                 .css('color', 'green');
           } else {
             tag = $('<a>', {text: 'too cool for me'})
               .addClass('followsyounot')
                 .css('color', '#666');
           }
           tag
             .attr('href', BASE_URL + '?username=' + screen_name)
               .attr('target', '_blank')
                 .attr('title', 'According to follows.me')
                   .css('float', 'right')
                     .css('padding-right', '30px')
                       .css('font-size', '11px')
                         .appendTo($('span.tweet-user-name', this));

         });
       });
     }
  }
})();

setTimeout(function() {
  Lookup.search();
  //$('a.tweet-screen-name').live(function() {
  //  Lookup.search();
  //});
  }, 2*1000);
