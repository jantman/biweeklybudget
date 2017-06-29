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
        this.html = '<form role="form" id="' + id + '">';
    }

    /**
     * Return complete rendered HTML for the form.
     *
     * @return {String} form HTML
     */
    render() {
        return this.html + "</form>\n";
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
     * Add a hidden input to the form.
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
     * Add a text input to the form.
     *
     * @param {String} id - The id of the form element
     * @param {String} name - The name of the form element
     * @param {String} label - The label text for the form element
     * @param {String} htmlClass - The HTML class to apply to the element
     * @return {FormBuilder} this
     */
    addText(id, name, label, htmlClass = 'form-control') {
        this.html += '<div class="form-group">' +
            '<label for="' + id + '" class="control-label">' + label + '</label>' +
            '<input class="' + htmlClass + '" id="' + id + '" name="' + name + '" type="text">' +
            '</div>\n';
        return this;
    }

}