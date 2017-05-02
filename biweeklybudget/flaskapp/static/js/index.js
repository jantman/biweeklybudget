$(function() {
  $.ajax('/ajax/chart-data/account-balances').done(function(ajaxdata) {
    Morris.Line({
      element: 'account-balance-chart',
      data: ajaxdata['data'],
      xkey: 'date',
      ykeys: ajaxdata['keys'],
      labels: ajaxdata['keys'],
      pointSize: 2,
      hideHover: 'auto',
      resize: true,
      preUnits: '$',
      continuousLine: true
    });
  });
});
