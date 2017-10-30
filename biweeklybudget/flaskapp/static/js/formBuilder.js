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
 * Create a new FormBuilder to generate an HTML form
 *
 * @param {String} id - The form HTML element ID.
 */
function FormBuilder(id) {
    this.form_id = id;
    this.html = "<!-- begin FormBuilder id=" + id + " -->\n" + '<form role="form" id="' + id + '">';
}

/**
 * Return complete rendered HTML for the form.
 *
 * @return {String} form HTML
 */
FormBuilder.prototype.render = function() {
    return this.html + "</form>\n<!-- end FormBuilder id=" + this.form_id + " -->\n";
};

/**
 * Add a paragraph (``p`` tag) to the form.
 *
 * @param {String} content - The content of the ``p`` tag.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addP = function(content) {
    this.html += '<p>' + content + "</p>\n";
    return this;
};

/**
 * Add a string of HTML to the form.
 *
 * @param {String} content - HTML
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addHTML = function(content) {
    this.html += content + "\n";
    return this;
};

/**
 * Add a hidden ``input`` to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} value - The value of the form element
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addHidden = function(id, name, value) {
    this.html += '<input type="hidden" id="' + id + '" name="' + name + '" value="' + value + '">\n';
    return this;
};

/**
 * Add a text ``input`` to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Object} options
 * @param {String} options.groupHtml - Additional HTML to add to the outermost
 * @param {String} options.inputHtml - extra HTML string to include in the
 *  actual ``input`` element *(optional; defaults to null)*
 * @param {String} options.helpBlock - Content for block of help text after input; defaults to null.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addText = function(id, name, label, options) {
    if(options === undefined) { options = {}; }
    options = $.extend({ groupHtml: null, inputHtml: null, helpBlock: null }, options);
    this.html += '<div class="form-group" id="' + id + '_group"';
    if(options.groupHtml !== null) { this.html += ' ' + options.groupHtml; }
    this.html += '><label for="' + id + '" class="control-label">' + label + '</label>' +
        '<input class="form-control" id="' + id + '" name="' + name + '" type="text"';
    if(options.inputHtml !== null) { this.html += ' ' + options.inputHtml; }
    this.html += '>';
    if (options.helpBlock !== null) {
        this.html += '<p class="help-block">' + options.helpBlock + "</p>";
    }
    this.html += '</div>\n';
    return this;
};

/**
 * Add a Text Area to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Object} options
 * @param {String} options.groupHtml - Additional HTML to add to the outermost
 * @param {String} options.inputHtml - extra HTML string to include in the
 *  actual ``input`` element *(optional; defaults to null)*
 * @param {String} options.helpBlock - Content for block of help text after input; defaults to null.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addTextArea = function(id, name, label, options) {
    if(options === undefined) { options = {}; }
    options = $.extend({ groupHtml: null, inputHtml: null, helpBlock: null }, options);
    this.html += '<div class="form-group" id="' + id + '_group"';
    if(options.groupHtml !== null) { this.html += ' ' + options.groupHtml; }
    this.html += '><label for="' + id + '" class="control-label">' + label + '</label>' +
        '<textarea class="form-control" id="' + id + '" name="' + name + '"';
    if(options.inputHtml !== null) { this.html += ' ' + options.inputHtml; }
    this.html += '></textarea>';
    if (options.helpBlock !== null) {
        this.html += '<p class="help-block">' + options.helpBlock + "</p>";
    }
    this.html += '</div>\n';
    return this;
};

/**
 * Add a text ``input`` for currency to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Object} options
 * @param {String} options.htmlClass - The HTML class to apply to the element; defaults to ``form-control``.
 * @param {String} options.helpBlock - Content for block of help text after input; defaults to null.
 * @param {String} options.groupHtml - Additional HTML to add to the outermost
 *  form-group div. This is where we'd usually add a default style/display. Defaults to null.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addCurrency = function(id, name, label, options) {
    if(options === undefined) { options = {}; }
    options = $.extend({ htmlClass: 'form-control', helpBlock: null, groupHtml: null }, options);
    this.html += '<div class="form-group" id="' + id + '_group"';
    if (options.groupHtml !== null) { this.html += ' ' + options.groupHtml; }
    this.html += '><label for="' + id + '" class="control-label">' + label + '</label>' +
        '<div class="input-group">' +
        '<span class="input-group-addon">' + CURRENCY_SYMBOL + '</span>' +
        '<input class="' + options.htmlClass + '" id="' + id + '" name="' + name + '" type="text">' +
        '</div>';
    if (options.helpBlock !== null) {
        this.html += '<p class="help-block">' + options.helpBlock + "</p>";
    }
    this.html += '</div>\n';
    return this;
};

/**
 * Add a date picker input to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Object} options
 * @param {String} options.groupHtml - Additional HTML to add to the outermost
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addDatePicker = function(id, name, label, options) {
    if(options === undefined) { options = {}; }
    options = $.extend({ groupHtml: null }, options);
    this.html += '<div class="form-group" id="' + id + '_group">' +
        '<label for="' + id + '" class="control-label">' + label + '</label>' +
        '<div class="input-group date" id="' + id + '_input_group">' +
        '<span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span>' +
        '<input class="form-control" id="' + id + '" name="' + name + '" type="text" size="12" maxlength="10">' +
        '</div>' +
        '</div>\n';
    return this;
};

/**
 * Add a select element to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Array} selectOptions - the options for the select, array of objects
 *  (order is preserved) each having the following attributes:
 * @param {String} selectOptions.label - the label for the option
 * @param {String} selectOptions.value - the value for the option
 * @param {Boolean} selectOptions.selected - whether the option should be the
 *  default selected value *(optional; defaults to False)*
 * @param {Object} options
 * @param {String} options.htmlClass - The HTML class to apply to the element; defaults to ``form-control``.
 * @param {String} options.helpBlock - Content for block of help text after input; defaults to null.
 * @param {String} options.groupHtml - Additional HTML to add to the outermost
 *  form-group div. This is where we'd usually add a default style/display. Defaults to null.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addSelect = function(id, name, label, selectOptions, options) {
    if(options === undefined) { options = {}; }
    options = $.extend({ htmlClass: 'form-control', helpBlock: null, groupHtml: null }, options);
    this.html += '<div class="form-group" id="' + id + '_group"';
    if (options.groupHtml !== null) { this.html += ' ' + options.groupHtml; }
    this.html += '><label for="' + id + '" class="control-label">' + label + '</label>' +
        '<select id="' + id + '" name="' + name + '" class="' + options.htmlClass + '">';
    for (var idx in selectOptions) {
        this.html += '<option value="' + selectOptions[idx].value + '"';
        if ('selected' in selectOptions[idx] && selectOptions[idx].selected === true) { this.html += ' selected="selected"'; }
        this.html += '>' + selectOptions[idx].label + '</option>';
    }
    this.html += '</select>';
    if (options.helpBlock !== null) {
        this.html += '<p class="help-block">' + options.helpBlock + "</p>";
    }
    this.html += '</div>\n';
    return this;
};

/**
 * Add a select element to the form, taking an Object of options where keys
 * are the labels and values are the values. This is a convenience wrapper
 * around :js:func:`budgetTransferDivForm`.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Object} selectOptions - the options for the select, label to value
 * @param {String} defaultValue - A value to select as the default
 * @param {Boolean} addNone - If true, prepend an option with a value of
 *  "None" and an empty label.
 * @param {Object} options - Options for rendering the control. Passed through
 *  unmodified to :js:func:`FormBuilder.addSelect`; see that for details.
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addLabelToValueSelect = function(id, name, label, selectOptions, defaultValue, addNone, options) {
    var built = [];
    if (addNone === true) {
        built.push({ value: 'None', label: '' });
        if(defaultValue === undefined) { defaultValue = 'None'; }
    }
    Object.keys(selectOptions).forEach(function (key) {
        var tmp = { value: selectOptions[key], label: key };
        if (defaultValue == selectOptions[key]) { tmp.selected = true; }
        built.push(tmp);
    });
    return this.addSelect(id, name, label, built, options);
};

/**
 * Add an inline radio button set to the form.
 *
 * Options is an Array of Objects, each object having keys ``id``, ``value``
 * and ``label``. Optional keys are ``checked`` (Boolean) and ``onchange``,
 * which will have its value placed literally in the HTML.
 *
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Array} options - the options for the select; array of objects
 *  each having the following attributes:
 * @param {String} options.id - the ID for the option
 * @param {String} options.value - the value for the option
 * @param {String} options.label - the label for the option
 * @param {Boolean} options.checked - whether the option should be checked
 *  by default *(optional; defaults to false)*
 * @param {String} options.inputHtml - extra HTML string to include in the
 *  actual ``input`` element *(optional; defaults to null)*
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addRadioInline = function(name, label, options) {
    this.html += '<div class="form-group" id="' + name + '_group"><label class="control-label">' + label + ' </label> ';
    for (var idx in options) {
        var o = options[idx];
        this.html += '<label class="radio-inline" for="' + o.id + '">' +
            '<input type="radio" name="' + name + '" id="' + o.id + '" value="' + o.value + '"';
        if ('inputHtml' in o) { this.html += ' ' + o.inputHtml; }
        if ('checked' in o && o.checked === true ) { this.html += ' checked'; }
        this.html += '>' + o.label + '</label>';
    }
    this.html += '</div>\n';
    return this;
};

/**
 * Add a checkbox to the form.
 *
 * @param {String} id - The id of the form element
 * @param {String} name - The name of the form element
 * @param {String} label - The label text for the form element
 * @param {Boolean} checked - Whether to default to checked or not
 * @return {FormBuilder} this
 */
FormBuilder.prototype.addCheckbox = function(id, name, label, checked) {
    this.html += '<div class="form-group" id="' + id + '_group">' +
        '<label class="checkbox-inline control-label" for="' + id + '">' +
        '<input type="checkbox" id="' + id + '" name="' + name + '"';
    if (checked === true) { this.html += ' checked'; }
    this.html += '> ' + label + '</label></div>\n';
    return this;
};
