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
     * @return {FormBuilder} this
     */
    addCurrency(id, name, label, opts = {}) {
        opts = $.extend({ htmlClass: 'form-control', helpBlock: null }, opts);
        this.html += '<div class="form-group">' +
            '<label for="' + id + '" class="control-label">' + label + '</label>' +
            '<div class="input-group">' +
            '<span class="input-group-addon">$</span>' +
            '<input class="' + opts['htmlClass'] + '" id="' + id + '" name="' + name + '" type="text">' +
            '</div>';
        if (opts['help_block'] !== null) {
            this.html += '<p class="help-block">' + opts['help_block'] + "</p>";
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
     * Options can either be an object or an array of objects. If an object, its
     * keys are used for the textual content of each option, and its values are
     * used for the option value. If an array of objects, order is preserved and
     * each object must have ``value`` and ``label`` keys, and can optionally
     * have a ``selected`` key with a boolean value.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {Array} options - the options for the select, array of objects
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

}