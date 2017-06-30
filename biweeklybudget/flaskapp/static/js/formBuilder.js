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

/** Class to build and render HTML forms */
class FormBuilder {

    /**
     * Create a new FormBuilder to generate an HTML form
     *
     * @param {String} id - The form HTML element ID.
     */
    constructor(id) {
        this.form_id = id;
        this.html = "<!-- begin FormBuilder id=" + id + " -->\n" + '<form role="form" id="' + id + '">';
    }

    /**
     * Return complete rendered HTML for the form.
     *
     * @return {String} form HTML
     */
    render() {
        return this.html + "</form>\n<!-- end FormBuilder id=" + this.form_id + " -->\n";
    }

    /**
     * Add a paragraph (``p`` tag) to the form.
     *
     * @param {String} content - The content of the ``p`` tag.
     * @return {FormBuilder} this
     */
    addP(content) {
        this.html += '<p>' + content + "</p>\n";
        return this;
    }

    /**
     * Add a hidden ``input`` to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} value - The value of the form element
     * @return {FormBuilder} this
     */
    addHidden(id, name, value) {
        this.html += '<input type="hidden" id="' + id + '" name="' + name + '" value="' + value + '">\n';
        return this;
    }

    /**
     * Add a text ``input`` to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @return {FormBuilder} this
     */
    addText(id, name, label) {
        this.html += '<div class="form-group">' +
            '<label for="' + id + '" class="control-label">' + label + '</label>' +
            '<input class="form-control" id="' + id + '" name="' + name + '" type="text">' +
            '</div>\n';
        return this;
    }

    /**
     * Add a text ``input`` for currency to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {Object} options
     * @param {String} options.htmlClass - The HTML class to apply to the element
     * @param {String} options.helpBlock - Content for block of help text after input
     * @param {String} options.groupHtml - Additional HTML to add to the outermost
     *  form-group div. This is where we'd usually add a default style/display.
     * @return {FormBuilder} this
     */
    addCurrency(id, name, label, opts = {}) {
        opts = $.extend({ htmlClass: 'form-control', helpBlock: null, groupHtml: null }, opts);
        this.html += '<div class="form-group" id="' + id + '_group"';
        if (opts['groupHtml'] !== null) { this.html += ' ' + opts['groupHtml']; }
        this.html += '><label for="' + id + '" class="control-label">' + label + '</label>' +
            '<div class="input-group">' +
            '<span class="input-group-addon">$</span>' +
            '<input class="' + opts['htmlClass'] + '" id="' + id + '" name="' + name + '" type="text">' +
            '</div>';
        if (opts['helpBlock'] !== null) {
            this.html += '<p class="help-block">' + opts['helpBlock'] + "</p>";
        }
        this.html += '</div>\n';
        return this;
    }

    /**
     * Add a date picker input to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @return {FormBuilder} this
     */
    addDatePicker(id, name, label) {
        this.html += '<div class="form-group" id="' + id + '_group">' +
            '<label for="' + id + '" class="control-label">' + label + '</label>' +
            '<div class="input-group date" id="' + id + '_input_group">' +
            '<span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span>' +
            '<input class="form-control" id="' + id + '" name="' + name + '" type="text" size="12" maxlength="10">' +
            '</div>' +
            '</div>\n';
        return this;
    }

    /**
     * Add a select element to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {Array} options - the options for the select, array of objects
     *  (order is preserved) each having the following attributes:
     * @param {String} options.label - the label for the option
     * @param {String} options.value - the value for the option
     * @param {Boolean} options.selected - whether the option should be the
     *  default selected value *(optional; defaults to False)*
     * @return {FormBuilder} this
     */
    addSelect(id, name, label, options) {
        this.html += '<div class="form-group"><label for="' + id + '" class="control-label">' + label + '</label>' +
            '<select id="' + id + '" name="' + name + '" class="form-control">';
        for (var idx in options) {
            this.html += '<option value="' + options[idx]['value'] + '"';
            if ('selected' in options[idx] && options[idx]['selected'] === true) { this.html += ' selected="selected"'; }
            this.html += '>' + options[idx]['label'] + '</option>';
        }
        this.html += '</select></div>\n';
        return this;
    }

    /**
     * Add a select element to the form, taking an Object of options where keys
     * are the labels and values are the values. This is a convenience wrapper
     * around :js:func:`budgetTransferDivForm`.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {Object} options - the options for the select, label to value
     * @param {String} defaultValue - A value to select as the default
     * @param {Boolean} addNone - If true, prepend an option with a value of
     *  "None" and an empty label.
     * @return {FormBuilder} this
     */
    addLabelToValueSelect(id, name, label, options, defaultValue, addNone = false) {
        var built = [];
        if (addNone === true) {
            built.push({ value: 'None', label: '' });
            if(defaultValue === undefined) { defaultValue = 'None'; }
        }
        Object.keys(options).forEach(function (key) {
            var tmp = { value: options[key], label: key };
            if (defaultValue == options[key]) { tmp['selected'] = true; }
            built.push(tmp);
        });
        return this.addSelect(id, name, label, built);
    }

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
    addRadioInline(name, label, options) {
        this.html += '<div class="form-group"><label class="control-label">' + label + ' </label> ';
        for (var idx in options) {
            var o = options[idx];
            this.html += '<label class="radio-inline" for="' + o['id'] + '">' +
                '<input type="radio" name="' + name + '" id="' + o['id'] + '" value="' + o['value'] + '"';
            if ('inputHtml' in o) { this.html += ' ' + o['inputHtml']; }
            if ('checked' in o && o['checked'] === true ) { this.html += ' checked'; }
            this.html += '>' + o['label'] + '</label>';
        }
        this.html += '</div>\n';
        return this;
    }

    /**
     * Add a checkbox to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {Boolean} checked - Whether to default to checked or not
     * @return {FormBuilder} this
     */
    addCheckbox(id, name, label, checked = false) {
        this.html += '<div class="form-group">' +
            '<label class="checkbox-inline control-label" for="' + id + '">' +
            '<input type="checkbox" id="' + id + '" name="' + name + '"';
        if (checked === true) { this.html += ' checked'; }
        this.html += '> ' + label + '</label></div>\n';
        return this;
    }

}