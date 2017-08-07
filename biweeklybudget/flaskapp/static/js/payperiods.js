// This is from https://github.com/uxsolutions/bootstrap-datepicker/issues/1154#issuecomment-280665688
//  (via https://jsfiddle.net/v6q2rxs0/39/)
$('.calendar').map(function(index) {
  $(this).datepicker({
  	defaultViewDate: {
      year: BIWEEKLYBUDGET_DEFAULT_DATE.getFullYear(),
      month: BIWEEKLYBUDGET_DEFAULT_DATE.getMonth() + (index - 1),
      date: 1
    },
    multidate: true,
    updateViewDate: false,
    format: "yyyy-mm-dd",
    todayHighlight: true
  }).on('changeDate', function(e) {
    window.location = "/pay_period_for?date=" + isoformat(e.date);
  });
});

// keep month in sync
var orderMonth = function(e) {
  var target = e.target;
  var date = e.date;
  var calendars = $('.calendar');
  var positionOfTarget = calendars.index(target);
  calendars.each(function(index) {
    if (this === target) {
      return;
    }
    var newDate = new Date(date);
    newDate.setUTCDate(1);
    newDate.setMonth(
      date.getMonth() + index - positionOfTarget
    );

    $(this).datepicker('_setDate', newDate, 'view');
  });
};
$('.calendar').on('changeMonth', orderMonth);

// keep dates in sync
$('.calendar').on('changeDate', function(e) {
  var calendars = $('.calendar');
  var target = e.target;
  var newDates = $(target).datepicker('getUTCDates');
  calendars.each(function() {
    if (this === e.target) {
    	return;
    }

    // setUTCDates triggers changeDate event
    // could easily run into an infinite loop
    // therefore we check if currentDates equal newDates
    var currentDates = $(this).datepicker('getUTCDates');
    if (
      currentDates &&
      currentDates.length === newDates.length &&
      currentDates.every(function(currentDate) {
 				return newDates.some(function(newDate) {
          return currentDate.toISOString() === newDate.toISOString();
        })
      })
    ) {
      return;
    }

    $(this).datepicker('setUTCDates', newDates);
  });
});

$('#payperiod-go-button').click(function() {
  var d = $('#payperiod_date_input').val();
  if(d != '' && d != 'YYYY-mm-dd') {
    window.location = "/pay_period_for?date=" + d;
  }
});

$('#payperiod_date_input').focus(function() {
  if($(this).val() == 'YYYY-mm-dd') { $(this).val(''); }
});