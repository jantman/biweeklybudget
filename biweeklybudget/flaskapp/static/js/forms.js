/*
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of biweeklybudget, also known as biweeklybudget.

    biweeklybudget is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    biweeklybudget is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with biweeklybudget.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/biweeklybudget> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
*/

/**
 * Generic function to handle form submission with server-side validation.
 *
 * See the Python server-side code for further information.
 *
 * @param {string} container_id - The ID of the container element (div) that is
 *  the visual parent of the form. On successful submission, this element will
 *  be emptied and replaced with a success message.
 * @param {string} form_id - The ID of the form itself.
 * @param {string} post_url - Relative URL to post form data to.
 * @param {Object} dataTableObj - passed on to ``handleFormSubmitted()``
 */
function handleForm(container_id, form_id, post_url, dataTableObj) {
    var data = serializeForm(form_id);
    $('.formfeedback').remove();
    $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
    $.ajax({
        type: "POST",
        url: post_url,
        data: data,
        success: function(data) {
            handleFormSubmitted(data, container_id, form_id, dataTableObj);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            handleFormError(jqXHR, textStatus, errorThrown, container_id, form_id);
        }
    });
}

/**
 * Return True if ``functionToCheck`` is a function, False otherwise.
 *
 * From: http://stackoverflow.com/a/7356528/211734
 *
 * @param {Object} functionToCheck - The object to test.
 */
function isFunction(functionToCheck) {
 var getType = {};
 return functionToCheck && getType.toString.call(functionToCheck) === '[object Function]';
}

/**
 * Handle the response from the API URL that the form data is POSTed to.
 *
 * This should either display a success message, or one or more error messages.
 *
 * @param {Object} data - response data
 * @param {string} container_id - the ID of the modal container on the page
 * @param {string} form_id - the ID of the form on the page
 * @param {Object} dataTableObj - A reference to the DataTable on the page, that
 *   needs to be refreshed. If null, reload the whole page. If a function, call
 *   that function. If false, do nothing.
 */
function handleFormSubmitted(data, container_id, form_id, dataTableObj) {
    if(data.hasOwnProperty('error_message')) {
        $('#' + container_id).prepend(
            '<div class="alert alert-danger formfeedback">' +
            '<strong>Server Error: </strong> ' + data.error_message + '</div>');
    } else if (data.hasOwnProperty('errors')) {
        var form = $('#' + form_id);
        Object.keys(data.errors).forEach(function (key) {
            var elem = form.find('[name=' + key + ']');
            data.errors[key].forEach( function(msg) {
                elem.parent().append('<p class="text-danger formfeedback">' + msg + '</p>');
                elem.parent().addClass('has-error');
            });
        });
    } else {
        $('#' + container_id).empty();
        $('#' + container_id).append('<div class="alert alert-success">' + data.success_message + '</div>');
        $('#modalSaveButton').hide();
        $('[data-dismiss="modal"]').click(function() {
            var oneitem_re = /\/\d+$/;
            if (dataTableObj === null || typeof dataTableObj == 'undefined') {
                // dataTableObj is null, refresh the page
                if (oneitem_re.test(window.location.href)) {
                    // don't reload if it will just show the modal again
                    var url = window.location.href.replace(/\/\d+$/, "");
                    window.location = url;
                } else {
                    location.reload();
                }
            } else if (isFunction(dataTableObj)) {
                // if it's a function, call it.
                dataTableObj(data);
            } else if (dataTableObj === false) {
                // do nothing
            } else if (dataTableObj !== null) {
                dataTableObj.api().ajax.reload();
            } else {
                console.log("ERROR: dataTableObj unknown type");
                console.log(dataTableObj);
            }
        });
    }
}

/**
 * Handle an error in the HTTP request to submit the form.
 */
function handleFormError(jqXHR, textStatus, errorThrown, container_id, form_id) {
    console.log("Form submission error: %s (%s)", textStatus, errorThrown);
    if($('#formStatus').length == 0) { $('#' + container_id).prepend('<div id="formStatus"></div>'); }
    $('#formStatus').html(
        '<div class="alert alert-danger formfeedback"><strong>Error submitting ' +
        'form:</strong> ' + textStatus + ': ' + jqXHR.status + ' ' + errorThrown + '</div>'
    );
}

/**
 * Generic function to handle form submission with server-side validation of
 * an inline (non-modal) form.
 *
 * See the Python server-side code for further information.
 *
 * @param {string} container_id - The ID of the container element (div) that is
 *  the visual parent of the form. On successful submission, this element will
 *  be emptied and replaced with a success message.
 * @param {string} form_id - The ID of the form itself.
 * @param {string} post_url - Relative URL to post form data to.
 * @param {Object} dataTableObj - passed on to ``handleFormSubmitted()``
 */
function handleInlineForm(container_id, form_id, post_url, dataTableObj) {
    var data = serializeForm(form_id);
    $('.formfeedback').remove();
    if($('#formStatus')) { $('#formStatus').empty(); }
    $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
    $.ajax({
        type: "POST",
        url: post_url,
        data: data,
        success: function(data) {
            handleInlineFormSubmitted(data, container_id, form_id, dataTableObj);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            handleInlineFormError(jqXHR, textStatus, errorThrown, container_id, form_id);
        }
    });
}

/**
 * Handle the response from the API URL that the form data is POSTed to, for an
 * inline (non-modal) form.
 *
 * This should either display a success message, or one or more error messages.
 *
 * @param {Object} data - response data
 * @param {string} container_id - the ID of the modal container on the page
 * @param {string} form_id - the ID of the form on the page
 * @param {Object} dataTableObj - A reference to the DataTable on the page, that
 *   needs to be refreshed. If null, reload the whole page. If a function, call
 *   that function. If false, do nothing.
 */
function handleInlineFormSubmitted(data, container_id, form_id, dataTableObj) {
    if($('#formStatus').length == 0) { $('#' + container_id).prepend('<div id="formStatus"></div>'); }
    if(data.hasOwnProperty('error_message')) {
        $('#formStatus').html(
            '<div class="alert alert-danger formfeedback">' +
            '<strong>Server Error: </strong> ' + data.error_message + '</div>'
        );
    } else if (data.hasOwnProperty('errors')) {
        var form = $('#' + form_id);
        Object.keys(data.errors).forEach(function (key) {
            var elem = form.find('[name=' + key + ']');
            data.errors[key].forEach( function(msg) {
                elem.parent().append('<p class="text-danger formfeedback">' + msg + '</p>');
                elem.parent().addClass('has-error');
            });
        });
    } else {
        $('#formStatus').empty();
        $('#formStatus').append('<div class="alert alert-success">' + data.success_message + '</div>');
        var oneitem_re = /\/\d+$/;
        if (dataTableObj === null || typeof dataTableObj == 'undefined') {
            // dataTableObj is null, refresh the page
            if (oneitem_re.test(window.location.href)) {
                // don't reload if it will just show the modal again
                var url = window.location.href.replace(/\/\d+$/, "");
                window.location = url;
            } else {
                location.reload();
            }
        } else if (isFunction(dataTableObj)) {
            // if it's a function, call it.
            dataTableObj(data);
        } else if (dataTableObj === false) {
            // do nothing
        } else if (dataTableObj !== null) {
            dataTableObj.api().ajax.reload();
        } else {
            console.log("ERROR: dataTableObj unknown type");
            console.log(dataTableObj);
        }
        setTimeout(
            function() { $('#formStatus').empty(); },
            2000
        );
    }
}

/**
 * Handle an error in the HTTP request to submit the inline (non-modal) form.
 */
function handleInlineFormError(jqXHR, textStatus, errorThrown, container_id, form_id) {
    console.log("Form submission error: %s (%s)", textStatus, errorThrown);
    if($('#formStatus').length == 0) { $('#' + container_id).prepend('<div id="formStatus"></div>'); }
    $('#formStatus').html(
        '<div class="alert alert-danger formfeedback"><strong>Error submitting ' +
        'form:</strong> ' + textStatus + ': ' + jqXHR.status + ' ' + errorThrown + '</div>'
    );
}

/**
 * Given the ID of a form, return an Object (hash/dict) of all data from it,
 * to POST to the server.
 *
 * @param {string} form_id - The ID of the form itself.
 */
function serializeForm(form_id) {
    var form = $('#' + form_id);
    var data = {};
    form.find('input').each(function(index) {
        var type = $(this).attr('type');
        if (type == 'text' || type == 'hidden') {
            data[$(this).attr('name')] = $(this).val();
        } else if (type == 'checkbox') {
            data[$(this).attr('name')] = $(this).prop('checked');
        } else if (type == 'radio') {
            if ($(this).prop('checked') === true) {
                if ($(this).prop('value') == 'true') {
                    data[$(this).attr('name')] = true;
                } else if ($(this).prop('value') == 'false') {
                    data[$(this).attr('name')] = false;
                } else {
                    data[$(this).attr('name')] = $(this).prop('value');
                }
            }
        } else {
            console.error(
                "Found form input with unknown type: %s (name=%s)",
                type, $(this).attr('name')
            );
        }
    });
    form.find('select').each(function(index) {
        data[$(this).attr('name')] = $(this).find(':selected').val();
    });
    form.find('textarea').each(function(index) {
        data[$(this).attr('name')] = $(this).val();
    });
    return data;
}
