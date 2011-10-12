function Chart(div_id, options) {
  this.div_id = div_id;
  this.options = options;
  this.data = new google.visualization.DataTable();
  this.data.addColumn('string', '#');
  this.data.addColumn('number', options.title);
  this.chart = new google.visualization.LineChart(document.getElementById(div_id));
  this.draw = function() {
    this.chart.draw(this.data, this.options);
  };
}


Chart.prototype.add_value = function(n) {
  // now we have at least 2 values
  this.data.addRow();
  var i = this.data.getNumberOfRows() - 1;
  this.data.setValue(i, 0, '' + (i + 1));
  this.data.setValue(i, 1, n);
  if (i > 0) {  // second iteration
    this.draw();
  }
}
