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

        $('#refresh span').text(CloudMonitor.refreshTimer);

      }, 1000);
    });
  },

  attachEventListeners: function() {
    $(document).on('click', '.metric', function() {
      var traces = $(this).data('path').split(',');
      CloudMonitor.Plot.toggleTraces(traces);
      $(this).toggleClass('plotted');

      if (CloudMonitor.Plot.traces.length > 0) {
        $('#export').removeClass('disabled');
      } else {
        $('#export').addClass('disabled');
      }
    });

    $('#refresh').on('click', function(e) {
      e.preventDefault();
      CloudMonitor.refresh();
      CloudMonitor.Plot.refresh();
    });

    $('#select-range').on('click', function(e) {
      e.preventDefault();
      $('#range').toggle();
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

      $('#select-range').text($(this).text())

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
    $('#refresh span').text(CloudMonitor.refreshTimer);

    $.post('/json', function(grids) {
      $.each(grids, function(grid_name, grid) {
        var $grid = $('.grid-' + grid_name)

        $.each(['cloud_monitor', 'cloud_scheduler', 'condor'], function(_, heartbeat) {
          var $heartbeat = $grid.find('.heartbeat-' + heartbeat);
          
          if (heartbeat in grid.heartbeat && grid.heartbeat[heartbeat] == 1) {
            $heartbeat.addClass('up');
            $heartbeat.removeClass('down');
          } else {
            $heartbeat.addClass('down');
            $heartbeat.removeClass('up');
          }
        });

        $.each(grid.clouds, function(cloud_name, cloud) {
          $.each(cloud.idle, function(vmtype, count) {
            var $cloud = $grid.find('.cloud-' + cloud_name + '.vmtype-' + vmtype);
            $cloud.find('.idle-vms').text(count);
          });

          $.each(cloud.vms, function(vmtype, vms) {
            var $cloud = $grid.find('.cloud-' + cloud_name + '.vmtype-' + vmtype);

            $.each(vms, function(status, count) {
              $cloud.find('.vms.' + status).text(count);
            });

            if (vms['hide']) $cloud.addClass('hide');
            else $cloud.removeClass('hide');
          });

          $.each(cloud.slots, function(vmtype, slots) {
            var $cloud = $grid.find('.cloud-' + cloud_name + '.vmtype-' + vmtype);

            $.each(slots, function(slot, count) {
              $cloud.find('.slots.' + slot).text(count);
            });
          });
        });

        $.each(grid.jobs, function(jobtype, statuses) {
          $.each(statuses, function(status, count) {
            $grid.find('.jobs.' + jobtype + '.' + status).text(count);
          });
        });
      });

      CloudMonitor.updateCellClasses();
    }, 'json');
  },

  updateCellClasses: function() {
    $('td.count').each(function() {
      if ($(this).text() == '0') $(this).addClass('zero');
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
