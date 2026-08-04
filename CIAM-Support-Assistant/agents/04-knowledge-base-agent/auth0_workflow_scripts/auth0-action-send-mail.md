# Auth0 Action: Send Mail

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Send Mail

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** a2ca2f6f-f5d7-4d0b-a011-262fa2914fa4

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api, fetch) => {
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

// Import necessary dependencies
    const userId = event.user.id;
    const accessToken = api.accessToken;
    // Check if the user is verified
    if (!event.user.email_verified) {
        // User is not verified, send a new verification email
        try {
            const responseData = await sendVerificationEmail(userId,accessToken);
            console.log('Verification email sent:', responseData);
        } catch (error) {
            console.error('Error sending verification email:', error);
        }
    }

    async function sendVerificationEmail(userId,accessToken) {
        try {
            // Use Auth0 Management API to send verification email
            const response = await fetch(
                'https://netskope-dev.us.auth0.com/api/v2/jobs/verification-email',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${accessToken}`
                    },
                    body: JSON.stringify({ user_id: userId })
                }
            );

            return await response.json();
        } catch (error) {
            throw error;
        }
    }

};


/**
* Handler that will be invoked when this action is resuming after an external redirect. If your
* onExecutePostLogin function does not perform a redirect, this function can be safely ignored.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
// exports.onContinuePostLogin = async (event, api) => {
// };

```
