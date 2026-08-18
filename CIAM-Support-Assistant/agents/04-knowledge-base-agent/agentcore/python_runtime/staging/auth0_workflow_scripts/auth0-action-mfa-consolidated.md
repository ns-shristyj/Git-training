# Auth0 Action: MFA - Consolidated

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### MFA - Consolidated

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 861d8569-fb64-4fc6-9383-860914b3fe96

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {

    //Don't apply MFA if the client ID matches the DLS_CID value or for the migration script.
    if (event.client.client_id === event.secrets.DLS_CID || event.client.client_id === event.secrets.b_id || event.user.app_metadata?.hasOwnProperty("skip_mfa") && event.user.app_metadata.skip_mfa === true) {
        api.multifactor.enable("none");
        return;
    };

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

    //Self-service MFA opt-in flow for NetskopeID, backed by DynamoDB
    if (event.connection.name === "NetskopeID") {
        var MFA_FORM = event.secrets.MFA_FORM;
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
                    let errorCode = await error_code_generator(new Error(), "1091");
                    USER.error = "Backend Error. Error ID: " + errorCode;
                    return USER;
                }
            }
            catch (error) {
                USER.user = null;
                let errorCode = await error_code_generator(new Error(), "1091");
                USER.error = "Backend Error. Error ID: " + errorCode;
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
                    let errorCode = await error_code_generator(new Error(), "1091");
                    USER.error = "Backend Error. Error ID: " + errorCode;
                    return USER;
                }   
            }
            catch (error) {
                USER.user = null;
                let errorCode = await error_code_generator(new Error(), "1091");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }

        var USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

        if (USER.user !== null) {
            USER = USER.user;
            if ((!event.authentication || !Array.isArray(event.authentication.methods) || !event.authentication.methods.find((method) => method.name === 'mfa'))) {
                if (!USER.hasOwnProperty("enable_mfa")) {
                    return(api.prompt.render(MFA_FORM));
                }
                else if (USER.hasOwnProperty("enable_mfa") && USER.enable_mfa === true) {
                    return(api.multifactor.enable("any"));
                }
                else if (USER.hasOwnProperty("enable_mfa") && USER.enable_mfa === false) {
                    if (event.stats.logins_count % 5 === 0) {
                        return(api.prompt.render(MFA_FORM));
                    }
                }
            }
            else {
                return;
            }
        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1091");
            return(api.access.deny("Backend Error. Error ID: " + errorCode));
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1091");
            return(api.access.deny("Backend Error. Error ID: " + errorCode));
        }
    }
    else if (event.connection.name !== "NetskopeID" && (!event.authentication || !Array.isArray(event.authentication.methods) || !event.authentication.methods.find((method) => method.name === 'mfa'))) {
        api.multifactor.enable("none");
        return;
    }
    else {
        api.multifactor.enable("any");
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
exports.onContinuePostLogin = async (event, api) => {
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }
    if (event.connection.name !== "NetskopeID" || event.client.client_id === event.secrets.DLS_CID) {
        api.multifactor.enable("none");
        return;
    };

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

    async function update_netskopeid_user(id, user) {
        const { marshall } = require("@aws-sdk/util-dynamodb");
        const { DynamoDBClient, UpdateItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");

        async function buildUpdateParams(tableName, key, updateObject) {
            const ExpressionAttributeNames = {};
            const ExpressionAttributeValues = {};
            const UpdateExpressions = [];

            for (const [field, value] of Object.entries(updateObject)) {
                const attrName = `#${field}`;
                const attrValue = `:${field}`;
                ExpressionAttributeNames[attrName] = field;
                ExpressionAttributeValues[attrValue] = value;
                UpdateExpressions.push(`${attrName} = ${attrValue}`);
            }

            return {
                TableName: tableName,
                Key: marshall({user_id: key}),
                UpdateExpression: `SET ${UpdateExpressions.join(", ")}`,
                ExpressionAttributeNames,
                ExpressionAttributeValues: marshall(ExpressionAttributeValues),
                ReturnValues: "ALL_NEW"
            }
        }

        var UPDATED = null;

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
                let errorCode = await error_code_generator(new Error(), "1091");
                UPDATED = "Backend error. Error ID: " + errorCode;
                return UPDATED;
            }
        }
        catch (error) {
            let errorCode = await error_code_generator(new Error(), "1091");
            UPDATED = "Backend error. Error ID: " + errorCode;
            return UPDATED;
        }

        const client = new DynamoDBClient({
            region: event.secrets.REG,
            credentials: {
                accessKeyId: stsResponse.Credentials.AccessKeyId,
                secretAccessKey: stsResponse.Credentials.SecretAccessKey,
                sessionToken: stsResponse.Credentials.SessionToken
            }
        });

        const updateObject = await buildUpdateParams(event.secrets.TN, id, user)

        const command = new UpdateItemCommand(
            updateObject
        );

        const response = await client.send(command);
        if (response.$metadata.hasOwnProperty("httpStatusCode") && response.$metadata.httpStatusCode === 200) {
            UPDATED = true;
            return UPDATED;
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1091");
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    if (event.connection.name === "NetskopeID" && event.prompt?.fields?.hasOwnProperty("enable_mfa")) {
        var update_object = {};
        var enable_mfa = event.prompt.fields.enable_mfa;
        if (enable_mfa === "yes" || enable_mfa === "Setup MFA Now") {
            enable_mfa = true;
            update_object = {"enable_mfa": enable_mfa};
            var UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
            if (UPDATED !== true) {
                return(api.multifactor.enable("any"));
            }
            else {
                return(api.multifactor.enable("any"));
            }
        }
        else if (enable_mfa === "no" || enable_mfa === "Skip & Remind Me Later") {
            enable_mfa = false;
            update_object = {"enable_mfa": enable_mfa};
            var UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
            if (UPDATED !== true) {
                return(api.multifactor.enable("none"));
            }
            else {
                return(api.multifactor.enable("none"));
            }
        }
    }
    else {
        return;
    }

};

```
