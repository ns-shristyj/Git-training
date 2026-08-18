# Auth0 Action: Gatekeeper

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Gatekeeper

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 35d76097-24c1-4b5b-b3cc-e853e286b7e6

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
    //Bypass any login events from the migration script.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

    //Retrive the user's profile from the NetskopeID table.
    async function get_netskopeid_user(id) {
        const { DynamoDBClient, GetItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");
        const { marshall,unmarshall } = require("@aws-sdk/util-dynamodb");

        var USER = {};

        // Create STS client
        const stsClient = new STSClient({
            region: event.secrets.REG,
            credentials: {
                accessKeyId: event.secrets.AKI,
                secretAccessKey: event.secrets.SAK
            }
        });
        // Assume role command
        const assumeRoleCommand = new AssumeRoleCommand({
            RoleArn: event.secrets.RAN,
            RoleSessionName: event.secrets.RSN,
            DurationSeconds: 900
        });
        // Get temporary credentials using STS
        var stsResponse = {};
        try {
            stsResponse = await stsClient.send(assumeRoleCommand);
            if (!stsResponse.hasOwnProperty("Credentials")) {
                USER.user = null;
                USER.error = "Backend error.";
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            USER.error = "Backend error: " + error;
            return USER;
        }

        const client = new DynamoDBClient({
            region: event.secrets.REG,
            credentials: {
                accessKeyId: stsResponse.Credentials.AccessKeyId,
                secretAccessKey: stsResponse.Credentials.SecretAccessKey,
                sessionToken: stsResponse.Credentials.SessionToken
            }
        });

        const command = new GetItemCommand({
            TableName: event.secrets.TN,
            Key: marshall({
                user_id: id
            }),
            ConsistentRead: true
        });

        try {
            const response = await client.send(command);
            if (response.hasOwnProperty("Item") && response.Item !== undefined && response.Item !== null) {
                USER.user = unmarshall(response.Item);
                return USER;
            }
            else {
                USER.user = null;
                USER.error = "Backend Error.";
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            USER.error = "Backend Error: " + error;
            return USER;
        }
    }
    
    if ((!event.user.app_metadata.entitlements.includes(event.client.metadata.entitlement) && !event.user.app_metadata.birthright.includes(event.client.metadata.entitlement)) || event.user.app_metadata.entitlements.includes(event.client.metadata.block)) {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        //api.session.revoke("Access Denied");
    }
    else if (event.user.app_metadata.hasOwnProperty('pending_community_user') && event.user.app_metadata.pending_community_user === true && (event.client?.metadata.entitlement??null) === "Community") {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        //api.session.revoke("Pending Approval");
        //api.access.deny("Pending Approval");
    }
    else if (event.user.app_metadata.hasOwnProperty('pending_support_user') && event.user.app_metadata.pending_support_user === true && (event.client?.metadata.entitlement??null) === "Support") {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        //api.session.revoke("Pending Approval");
        //api.access.deny("Pending Approval");
    }
    else if (event.user.app_metadata.hasOwnProperty('pending_community_approval') && (event.user.app_metadata.pending_community_approval === null || event.user.app_metadata.pending_community_approval === true) && (event.client?.metadata.entitlement??null) === "Community") {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        //api.session.revoke("Pending Approval");
        //api.access.deny("Pending Approval");
    }
    else {
        return;
    }

/*
  if (event.connection.name === "NetskopeID") {
    var USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

    if (USER.user !== null) {
      USER = USER.user;
      if ((!USER.entitlements.includes(event.client.metadata.entitlement) && !USER.birthright.includes(event.client.metadata.entitlement)) || USER.entitlements.includes(event.client.metadata.block)) {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        api.session.revoke("Access Denied");
      }
      else if (USER.hasOwnProperty('pending_community_user') && USER.pending_community_user === true && (event.client?.metadata.entitlement??null) === "Community") {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        api.session.revoke("Pending Approval");
        //api.access.deny("Pending Approval");
      }
      else if (USER.hasOwnProperty('pending_community_approval') && (USER.pending_community_approval === null || USER.pending_community_approval === true) && (event.client?.metadata.entitlement??null) === "Community") {
        const FORM_ID = event.secrets.form_id;
        api.prompt.render(FORM_ID);
        api.session.revoke("Pending Approval");
        //api.access.deny("Pending Approval");
      }
      else {
        return;
      }
    }
    else if (USER.error !== null) {
      console.log(USER.error);
    }
    else {
      console.log("Backend Error.")
    }
  }
*/
};


/**
* Handler that will be invoked when this action is resuming after an external redirect. If your
* onExecutePostLogin function does not perform a redirect, this function can be safely ignored.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
**/
exports.onContinuePostLogin = async (event, api) => {

    //Bypass any login events from the migration script.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

    if ((!event.user.app_metadata.entitlements.includes(event.client.metadata.entitlement) && !event.user.app_metadata.birthright.includes(event.client.metadata.entitlement)) || event.user.app_metadata.entitlements.includes(event.client.metadata.block)) {
        api.session.revoke("Access Denied");
    }
    else if (event.user.app_metadata.hasOwnProperty('pending_community_user') && event.user.app_metadata.pending_community_user === true && (event.client?.metadata.entitlement??null) === "Community") {
        api.session.revoke("Pending Approval");
    }
    else if (event.user.app_metadata.hasOwnProperty('pending_community_approval') && (event.user.app_metadata.pending_community_approval === null || event.user.app_metadata.pending_community_approval === true) && (event.client?.metadata.entitlement??null) === "Community") {
        api.session.revoke("Pending Approval");
    }
    else {
        return;
    }
};
```
