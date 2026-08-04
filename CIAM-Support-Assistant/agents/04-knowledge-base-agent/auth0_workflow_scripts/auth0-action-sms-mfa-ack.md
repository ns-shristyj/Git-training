# Auth0 Action: SMS-MFA-Ack

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### SMS-MFA-Ack

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** c004f739-ed13-4d42-a865-61cce8473efc

**Script:**
```javascript
/**
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
  api.prompt.render('ap_h2B79dQnBiHT1XLYPENpji');
}

/**
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onContinuePostLogin = async (event, api) => {
  //  Your logic after completing the form
}
```
