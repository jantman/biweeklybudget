/**
 * TEST FUNCTION - Initiate a Plaid link. This function is for testing only; it
 * directly POSTs to /ajax/plaid/get_access_token with
 *
 */
function plaidLink() {
    $.post('/ajax/plaid/get_access_token', {
        public_token: 'CItest'
    }, function(data) {
        console.log("get_access_token response: %o", data);
        $('#plaid_item_id').val(data.item_id);
        $('#plaid_token').val(data.access_token);
    }).fail(function() {
        alert("ERROR: /ajax/plaid/get_access_token callback failed; see server log for details.")
    });
}

/**
 * TEST FUNCTION - Update a Plaid link. This function is for testing only!
 */
function plaidUpdate() {
    console.log("called plaidUpdate()");
    $.post('/ajax/plaid/create_public_token',
        {access_token: $('#plaid_token').val()},
        function(data) {
            console.log("Got create_public_token response: %o", data);
        },
    ).fail(function() {
        alert("ERROR: /ajax/plaid/create_public_token callback failed; see server log for details.")
    });
}
