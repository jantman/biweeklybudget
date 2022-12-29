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
