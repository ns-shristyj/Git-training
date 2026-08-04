# Auth0 Action: Privacy Policy Acknowledgement

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Privacy Policy Acknowledgement

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** a2cb8443-25b6-4444-8e10-6d8c1c0fb159

**Script:**
```javascript
/**
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
    //Bypass any login events from the migration script.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

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

    //Retrive the user's profile from the NetskopeID table.
    async function get_netskopeid_user(id) {
        const { marshall,unmarshall } = require("@aws-sdk/util-dynamodb");
        const { DynamoDBClient, GetItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");


        let USER = {};

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
        let stsResponse = {};
        try {
            stsResponse = await stsClient.send(assumeRoleCommand);
            if (!stsResponse.hasOwnProperty("Credentials")) {
                USER.user = null;
                let errorCode = await error_code_generator(new Error(), "1031")
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1031");
            USER.error = "Backend error: " + error + ". Error ID: " + errorCode;
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
                let errorCode = await error_code_generator(new Error(), "1031");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1031");
            USER.error = "Backend Error. Error ID: " + errorCode;
            return USER;
        }
    }

    if (event.connection.name === "NetskopeID") {
        let USER = await get_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id));

        //Users with privacy_policy set to false or null are presented with the migration acknowledgement form.
        if (USER.user !== null && (USER.user.privacy_policy?USER.user.privacy_policy:false) === false) {
            console.log("User must accept the Netskope Privacy Policy to proceed.");
            const FORM_ID = event.secrets.form_id;
            api.prompt.render(FORM_ID);
        }
        //The user has already accecpted the privacy policy.
        else if (USER.user !== null && (USER.user.privacy_policy?USER.user.privacy_policy:false) === true) {
            console.log("User has already accepted the Netskope Privacy Policy.");
            return;
        }
        //The user could not be retreived from the NetskopeID table.
        else if (USER.user === null && USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1031");
            return(api.access.deny("Backend Error. Error ID: " + errorCode));
        }
        //The user could not be retreived from the NetskopeID table.
        else if (USER.user === null && USER.error === null) {
            let errorCode = await error_code_generator(new Error(), "1031");
            return(api.access.deny("Backend Error. Error ID: " + errorCode));
        }
    }
    else {
        return;
    }
}

/**
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onContinuePostLogin = async (event, api) => {
    //Bypass migration script login attempts.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

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

    //Update a user object in the NetskopeID table.
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
            };
        }

        let UPDATED = null;

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
        let stsResponse = {};
        try {
            stsResponse = await stsClient.send(assumeRoleCommand);
            if (!stsResponse.hasOwnProperty("Credentials")) {
                UPDATED = "Backend error.";
                return UPDATED;
            }
        }
        catch (error) {
            UPDATED = "Backend error: " + error;
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
            UPDATED = "Backend Error.";
            return UPDATED;
        }
    }

    //If we detect an input to the form, we update the user's NetskopeID table object with the input.
    if (event.connection.name === "NetskopeID" && event.prompt?.fields?.hasOwnProperty("privacy_policy")) {
        const dtn = Date.now();
        const dtu = (dtn-(dtn%1000))/1000;
        let privacy_policy = event.prompt.fields.privacy_policy;
        let update_object = {
            privacy_policy: privacy_policy,
            privacy_policy_timestamp: dtu,
        }
    
        let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
        if (UPDATED !== true) {
            let errorCode = await error_code_generator(new Error(), "1031");
            return(api.session.revoke("Backend Error. Error ID: " + errorCode));
        }
        if (privacy_policy === false) {
            return(api.session.revoke("The Netskope privacy policy was not accepted."));
        }
        return;
    }
    else {
        return;
    }
}
```
