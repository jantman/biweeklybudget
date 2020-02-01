/**
 * Initiate a Plaid link. Perform the link process and retrieve a public token;
 * POST it to /ajax/plaid/get_access_token and update from fields with the
 * result.
 */
function plaidLink() {
    console.log("Call plaidLink()");
    var handler = Plaid.create({
        apiVersion: 'v2',
        clientName: 'github.com/jantman/biweeklybudget ' + BIWEEKLYBUDGET_VERSION,
        env: PLAID_ENV,
        product: PLAID_PRODUCTS,
        key: PLAID_PUBLIC_KEY,
        countryCodes: PLAID_COUNTRY_CODES.split(','),
        onSuccess: function(public_token) {
            console.log("plaidLink onSuccess public_token=" + public_token);
            $.post('/ajax/plaid/get_access_token', {
                public_token: public_token
            }, function(data) {
                console.log("get_access_token response: %o", data);
                $('#plaid_item_id').val(data.item_id);
                $('#plaid_token').val(data.access_token);
            }).fail(function() {
                alert("ERROR: /ajax/plaid/get_access_token callback failed; see server log for details.")
            });
        },
    });
    console.log("plaidLink() call handler.open()");
    handler.open();
}

/**
 * Update the existing Plaid account / Link.
 */
function plaidUpdate() {
    console.log("called plaidUpdate()");
    $.post('/ajax/plaid/create_public_token',
        {access_token: $('#plaid_token').val()},
        function(data) {
            console.log("Call plaidLink() with public_token=" + data.public_token);
            var handler = Plaid.create({
                apiVersion: 'v2',
                clientName: 'github.com/jantman/biweeklybudget ' + BIWEEKLYBUDGET_VERSION,
                env: PLAID_ENV,
                product: PLAID_PRODUCTS,
                key: PLAID_PUBLIC_KEY,
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
