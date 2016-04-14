"use strict";

var CloudMonitor = {

  from: '-1h',
  end: 'now',

  refreshTimer: 60,
  refreshInterval: null,

  initialize: function() {
    $(document).on('ready', function() {
      CloudMonitor.attachEventListeners();
      CloudMonitor.updateCellClasses();

      CloudMonitor.Plot.initialize();

      CloudMonitor.refreshInterval = setInterval(function() {
        CloudMonitor.refreshTimer--;

        if (CloudMonitor.refreshTimer == 0) {
          CloudMonitor.refresh();
          CloudMonitor.Plot.refresh();
        }

        $('#refresh-timer').text(CloudMonitor.refreshTimer);

      }, 1000);
    });
  },

  attachEventListeners: function() {
    $(document).on('click', '.metric', function() {
      var traces = $(this).data('path').split('|');
      CloudMonitor.Plot.toggleTraces(traces);
      $(this).toggleClass('plotted');

      if (CloudMonitor.Plot.traces.length > 0) {
        $('#export').parent().removeClass('disabled');
      } else {
        $('#export').parent().addClass('disabled');
      }
    });

    $('#refresh').on('click', function(e) {
      e.preventDefault();
      CloudMonitor.refresh();
      CloudMonitor.Plot.refresh();
    });

    $('#set-options').on('click', function(e) {
      e.preventDefault();
      $('#options').toggle();
    });

    $('#export').on('click', function(e) {
      e.preventDefault();
      if (CloudMonitor.Plot.traces.length > 0) {
        window.open('/export?' + $.param({ paths: CloudMonitor.Plot.traces, from: CloudMonitor.from, end: CloudMonitor.end }));
      }
    });

    $('a.date-range').on('click', function(e) {
      e.preventDefault();

      CloudMonitor.setRange($(this).data('from'), $(this).data('end'));

      $('#date-range-from').val(CloudMonitor.from);
      $('#date-range-end').val(CloudMonitor.end);

      $('a.date-range').removeClass('selected');
      $(this).addClass('selected');

      $('#selected-range').text($(this).text())

      CloudMonitor.Plot.refresh();
    });

    $('#apply-date-range').on('click', function(e) {
      e.preventDefault();

      CloudMonitor.setRange($('#date-range-from').val(), $('#date-range-end').val());

      $('a.date-range').removeClass('selected');

      var link = $('a.date-range[data-from="' + CloudMonitor.from + '"][data-end="' + CloudMonitor.end + '"]');
      if (link.length) {
        link.addClass('selected');
        $('#select-range').text(link.text())
      } else {
        $('#select-range').text('From ' + CloudMonitor.from + ' to ' + CloudMonitor.end);
      }

      CloudMonitor.Plot.refresh();
    });

    $('#save-options').on('click', function(e) {
      e.preventDefault();
      CloudMonitor.setOptions({
        showAllClouds: $('#show-all-clouds').prop('checked')
      });
      $('#options').hide();
    });

    $('#plot').on('plotly_relayout', function(e) {
      var timeRange = CloudMonitor.Plot.el.layout.xaxis.range;
      CloudMonitor.setRange(timeRange[0], timeRange[1]);
    });
  },

  setRange: function(setFrom, setEnd) {
    CloudMonitor.from = setFrom;
    CloudMonitor.end  = setEnd;
    CloudMonitor.Plot.refresh();
  },

  refresh: function() {
    CloudMonitor.refreshTimer = 60;
    $('#refresh-timer').text(CloudMonitor.refreshTimer);
    
    $.post('?refresh', function(data) {
      $('#content').html(data);
      CloudMonitor.updateCellClasses();
    }, 'html');
  },

  updateCellClasses: function() {
    $('td.count').each(function() {
      if ($(this).text().trim() == '0') $(this).addClass('zero');
      else $(this).removeClass('zero');
    });
  },

  setOptions: function(opts) {
    if (opts.showAllClouds) {
      $('table').addClass('show-all');
    } else {
      $('table').removeClass('show-all');
    }
  }
}

CloudMonitor.Plot = {
  Layout: {
    paper_bgcolor: '#fff',
    plot_bgcolor: '#fff',

    margin: {
      l: 50,
      r: 50,
      t: 20,
      b: 50
    },

    yaxis: {
      rangemode: 'tozero'
    }
  },

  showing: false,
  el: null,
  traces: [],

  initialize: function() {
    CloudMonitor.Plot.el = $('#plot')[0];

    $('#close-plot').on('click', function(e) {
      e.preventDefault();
      CloudMonitor.Plot.hide();
      $('.metric').removeClass('plotted');
      $('#export').parent().addClass('disabled');
    });

    $(window).on('resize', function() {
        Plotly.Plots.resize(CloudMonitor.Plot.el);
    });
  },

  toggleTraces: function(traces) {
    if (!$.isArray(traces)) traces = [traces];

    $.each(traces, function(_, trace) {
      var index = CloudMonitor.Plot.traces.indexOf(trace);

      if (index < 0) {
        CloudMonitor.Plot.traces.push(trace);
      } else {
        CloudMonitor.Plot.traces.splice(index, 1);
      }
    });

    if (CloudMonitor.Plot.traces.length > 0) {
      CloudMonitor.Plot.show();
    } else {
      CloudMonitor.Plot.hide();
    }

    // Refresh the plot to load the new trace
    CloudMonitor.Plot.refresh();
  },

  refresh: function() {
    if (!CloudMonitor.Plot.showing) return;

    $.post('/json', { paths: CloudMonitor.Plot.traces, from: CloudMonitor.from, end: CloudMonitor.end }, function(data) {
      Plotly.newPlot(CloudMonitor.Plot.el, data, CloudMonitor.Plot.Layout, { displayModeBar: false });
      $(CloudMonitor.Plot.el).find('.svg-container').show();
    }, 'json');
  },

  show: function() {
    CloudMonitor.Plot.showing = true;

    $('.plot').show();
  },

  hide: function() {
    CloudMonitor.Plot.traces = [];
    CloudMonitor.Plot.showing = false;

    $('.plot').hide();
    $(CloudMonitor.Plot.el).find('.svg-container').hide();
    $('#export').addClass('disabled');
  }
}

CloudMonitor.initialize();
