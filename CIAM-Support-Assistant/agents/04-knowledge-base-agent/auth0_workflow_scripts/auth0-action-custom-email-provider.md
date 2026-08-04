# Auth0 Action: Custom Email Provider

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Custom Email Provider

- **Trigger(s):** custom-email-provider
- **Status:** built
- **Action ID:** c15b0b4d-7078-4ee8-b5a5-72fab00646d1

**Script:**
```javascript
/**
* Handler to be executed while sending an email notification
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {CustomEmailProviderAPI} api - Methods and utilities to help change the behavior of sending a email notification.
*/
exports.onExecuteCustomEmailProvider = async (event, api) => {
  // Code goes here
  return;
};
```
