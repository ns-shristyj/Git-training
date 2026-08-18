# Auth0 Action: Email Verification v2

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Email Verification v2

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** c291294f-d667-4e29-9102-70eb8ecca282

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
    

    //This function generates error codes based error stack trace.
    async function error_code_generator(e, code) {
        const { v4: uuidv4 } = require("uuid");
        const regex = /\((.*):(\d+):(\d+)\)$/;
        const match = regex.exec(e.stack.split("\n")[1]);
        let uuid = uuidv4();
        let d = uuid.split("-");
        d[0] = code + (match && match[2] ? match[2].toString() : '') + (match && match[3] ? match[3].toString() : '');
        let newCode = d.join("-");
        return newCode;
    }

    //Bypass migration script related logins.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

    //ID of the Email Verification form.
    const FORM_ID = event.secrets.form_id;

    if (!event.user.email_verified) {
        const ManagementClient = require('auth0').ManagementClient;

        const management = new ManagementClient({
            domain: event.secrets.domain,
            clientId: event.secrets.client_id,
            clientSecret: event.secrets.client_secret
        });

        let params = {}
        if (event.connection.name === "NetskopeID") {
            params = {
                client_id: event.client.client_id,
                user_id: event.user.user_id,
                identity: {
                    user_id: event.user.user_id.split('|')[1],
                    provider: event.user.user_id.split('|')[0]
                }
            };
        }
        else if  (event.connection.name !== "NetskopeID") {
            params = {
                client_id: event.client.client_id,
                user_id: event.user.user_id,
                identity: {
                    user_id: event.user.user_id.split('|').slice(1).join('|'),
                    provider: event.user.user_id.split('|')[0]
                }
            };
        }

        try {
            await management.jobs.verificationEmail.create(params, async function (err) {
                if (err && err instanceof Error) {
                    const errorCode = await error_code_generator(new Error(), "1011");
                    console.error("Backend Error. Error ID: " + errorCode);
                }
            });

            api.prompt.render(FORM_ID);
        }
        catch (error) {
            const errorCode = await error_code_generator(new Error(), "1011");
            api.session.revoke("Backend Error. Error ID: " + errorCode);
        }
    }
    else {
        return;
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
