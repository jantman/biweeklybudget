/**
 * Initiate a Plaid link. Perform the link process and retrieve a public token;
 * POST it to /ajax/plaid/handle_link.
 */
function plaidLink() {
    console.log("Call plaidLink()");
    var handler = Plaid.create({
        apiVersion: 'v2',
        clientName: 'github.com/jantman/biweeklybudget ' + BIWEEKLYBUDGET_VERSION,
        env: PLAID_ENV,
        product: PLAID_PRODUCTS,
        countryCodes: PLAID_COUNTRY_CODES.split(','),
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
                    console.log("get_access_token response: %o; reloading", data);
                    location.reload();
                },
                error: function() {
                    alert("ERROR: /ajax/plaid/handle_link callback failed; see server log for details.");
                }
            });
        },
    });
    console.log("plaidLink() call handler.open()");
    handler.open();
}

/**
 * Update the existing Plaid account / Link.
 */
function plaidUpdate(item_id) {
    console.log("called plaidUpdate(" + item_id + ")");
    $.post('/ajax/plaid/create_public_token',
        {item_id: item_id},
        function(data) {
            console.log("Call plaidLink() with public_token=" + data.public_token);
            var handler = Plaid.create({
                apiVersion: 'v2',
                clientName: 'github.com/jantman/biweeklybudget ' + BIWEEKLYBUDGET_VERSION,
                env: PLAID_ENV,
                product: PLAID_PRODUCTS,
                token: data.public_token,
                countryCodes: PLAID_COUNTRY_CODES.split(','),
                onSuccess: function() {
                    console.log("plaidUpdate() SUCCESS!");
                    alert("Plaid Update success!");
                },
            });
            console.log("plaidLink() call handler.open()");
            handler.open();
        },
    ).fail(function() {
        alert("ERROR: /ajax/plaid/create_public_token callback failed; see server log for details.")
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
