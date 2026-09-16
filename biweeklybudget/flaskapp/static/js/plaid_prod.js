/**
 * Initiate a Plaid link. Perform the link process and retrieve a public token;
 * POST it to /ajax/plaid/handle_link.
 */
function plaidLink() {
    console.log("Call plaidLink()");
    $.ajax({
        url: '/ajax/plaid/create_link_token',
        type: 'POST',
        data: JSON.stringify({"type": "new_link"}),
        dataType: 'json',
        contentType: 'application/json',
        success: function(data) {
            console.log("create_link_token onSuccess data=" + data);
            var handler = Plaid.create({
                token: data.link_token,
                onSuccess: function(public_token, metadata) {
                    console.log("plaidLink onSuccess public_token=" + public_token + " metadata=" + metadata);
                    $.ajax({
                        url: '/ajax/plaid/handle_link',
                        type: 'POST',
                        data: JSON.stringify({
                            public_token: public_token,
                            metadata: metadata
                        }),
                        dataType: 'json',
                        contentType: 'application/json',
                        success: function(data) {
                            console.log("exchange_public_token response: %o; reloading", data);
                            location.reload();
                        },
                        error: function() {
                            alert("ERROR: /ajax/plaid/exchange_public_token callback failed; see server log for details.");
                        }
                    });
                },
                onExit: function(err, metadata) {
                    console.log("Metadata: " + metadata);
                    // 2b. Gracefully handle the invalid link token error. A link token
                    // can become invalidated if it expires, has already been used
                    // for a link session, or is associated with too many invalid logins.
                    if (err != null && err.error_code === 'INVALID_LINK_TOKEN') {
                        console.log("ERROR: INVALID_LINK_TOKEN");
                        alert("ERROR: INVALID_LINK_TOKEN; please try again.");
                    }
                    if (err != null) {
                        console.log("ERROR: " + err);
                        alert("ERROR: Plaid Link failed.");
                    }
                }
            });
            console.log("plaidLink() call handler.open()");
            handler.open();
        },
        error: function() {
            console.log("ERROR: /ajax/plaid/create_link_token callback failed; see server log for details.");
            alert("ERROR: /ajax/plaid/create_link_token callback failed; see server log for details.");
        }
    });
}

/**
 * Update the existing Plaid account / Link.
 */
function plaidUpdate(item_id) {
    console.log("called plaidUpdate(" + item_id + ")");
    $.ajax({
        url: '/ajax/plaid/create_link_token',
        type: 'POST',
        data: JSON.stringify({"item_id": item_id}),
        dataType: 'json',
        contentType: 'application/json',
        success: function(data) {
            console.log("plaid_update create_link_token callback onSuccess data=" + data);
            var handler = Plaid.create({
                token: data.link_token,
                onSuccess: function() {
                    console.log("plaidUpdate() SUCCESS!");
                    alert("Plaid Update success!");
                },
                onExit: function(err, metadata) {
                    console.log("Metadata: " + metadata);
                    // 2b. Gracefully handle the invalid link token error. A link token
                    // can become invalidated if it expires, has already been used
                    // for a link session, or is associated with too many invalid logins.
                    if (err != null && err.error_code === 'INVALID_LINK_TOKEN') {
                        console.log("ERROR: INVALID_LINK_TOKEN");
                        alert("ERROR: INVALID_LINK_TOKEN; please try again.");
                    }
                    if (err != null) {
                        console.log("ERROR: " + err);
                        alert("ERROR: Plaid Link failed.");
                    }
                }
            });
            console.log("plaidLink() call handler.open()");
            handler.open();
        },
        error: function() {
            console.log("ERROR: /plaid_update ajax/plaid/create_link_token callback failed; see server log for details.");
            alert("ERROR: plaid_update /ajax/plaid/create_link_token callback failed; see server log for details.");
        }
    });
}

/**
 * Call the /ajax/plaid/refresh_item_accounts endpoint and then reload this page.
 */
function plaidRefresh(item_id) {
    console.log("called plaidRefresh(" + item_id + ")");
    $.ajax({
        url: '/ajax/plaid/refresh_item_accounts',
        type: 'POST',
        data: JSON.stringify({
            item_id: item_id
        }),
        dataType: 'json',
        contentType: 'application/json',
        success: function(data) {
            location.reload();
        },
        error: function() {
            alert("ERROR: /ajax/plaid/refresh_item_accounts callback failed; see server log for details.");
        }
    });
}

/**
 * Show the confirmation modal for deleting a Plaid Item. Makes no request of
 * its own; the deletion happens in :js:func:`plaidDelete`, called when the
 * modal's Delete button is clicked.
 *
 * @param {string} item_id - the Plaid Item ID to delete.
 * @param {string} institution_name - the Item's institution name, for display.
 * @param {string} account_names - comma-separated "Name (id)" for each Account
 *   linked to this Item, or an empty string if none are.
 */
function plaidDeleteConfirm(item_id, institution_name, account_names) {
    console.log("called plaidDeleteConfirm(" + item_id + ")");
    var accts = (account_names || '').trim();
    var acctText = accts === '' ?
        'No Accounts are linked to this Item, so none will be un-linked.' :
        'These Accounts will no longer be linked to Plaid, but will keep all ' +
        'of their transactions, balances and history: ' + accts + '.';
    $('#modalBody').empty();
    $('#modalBody').append(
        $('<div id="plaidDeleteConfirmBody"/>')
            .append($('<p/>').text(
                'Delete Plaid Item ' + item_id + ' (' + institution_name +
                ')?'
            ))
            .append($('<p/>').text(acctText))
            .append($('<p/>').text(
                'The Item will also be removed at Plaid, and its Plaid ' +
                'Accounts will be removed from biweeklybudget. This cannot ' +
                'be undone; to use this institution again you must link it ' +
                'from scratch.'
            ))
    );
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        plaidDelete(item_id);
    });
    $('#modalSaveButton').text('Delete')
        .removeClass('btn-primary').addClass('btn-danger').show();
    $('#modalLabel').text('Delete Plaid Item ' + item_id);
    $("#modalDiv").modal('show');
}

/**
 * Call the /ajax/plaid/delete_item endpoint and then reload this page. On
 * failure, show the server's message and leave the page alone, since nothing
 * was deleted.
 *
 * @param {string} item_id - the Plaid Item ID to delete.
 */
function plaidDelete(item_id) {
    console.log("called plaidDelete(" + item_id + ")");
    $.ajax({
        url: '/ajax/plaid/delete_item',
        type: 'POST',
        data: JSON.stringify({
            item_id: item_id
        }),
        dataType: 'json',
        contentType: 'application/json',
        success: function(data) {
            location.reload();
        },
        error: function(jqXHR) {
            var msg = "see server log for details.";
            if (jqXHR.responseJSON && jqXHR.responseJSON.message) {
                msg = jqXHR.responseJSON.message;
            }
            $("#modalDiv").modal('hide');
            alert(
                "ERROR deleting Plaid Item " + item_id + "; nothing was " +
                "deleted: " + msg
            );
        }
    });
}
