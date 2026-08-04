# Auth0 Action: Account Migration Acknowledgement

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Account Migration Acknowledgement

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 3c311f69-8a50-490e-b2b9-55ddb51d2181

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
        d[0] = d[0] = code + (match && match[2] ? match[2].toString() : '') + (match && match[3] ? match[3].toString() : '');
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
                const errorCode = await error_code_generator(new Error(), "1021")
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            const errorCode = await error_code_generator(new Error(), "1021")
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
            Key: marshall({user_id: id}),
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
                const errorCode = await error_code_generator(new Error(), "1021")
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            const errorCode = await error_code_generator(new Error(), "1021")
            USER.error = "Backend Error. Error ID: " + errorCode;
            return USER;
        }
    }

    if (event.connection.name === "NetskopeID") {
        let USER = await get_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id));

        //There is no need to present the migration acknowledgement for these users.
        if (USER.user !== null && USER.user.hasOwnProperty("migration_policy") === false) {
            return;
        }
        //Users with migration_policy set to false are presented with the migration acknowledgement form.
        else if (USER.user !== null && USER.user.migration_policy === false) {
            console.log("You must accept the account migration acknowledgement to proceed.");
            const FORM_ID = event.secrets.form_id;
            api.prompt.render(FORM_ID);
        }
        //The user has already accecpted the acknowledgement.
        else if (USER.user !== null && USER.user.migration_policy === true) {
            console.log("You have already accepted the account migration acknowledgement. Thank you!");
            return;
        }
        //The user could not be retreived from the NetskopeID table.
        else if (USER.user === null && USER.error !== null) {
            const errorCode = await error_code_generator(new Error(), "1021")
            return(api.session.revoke("Backend Error. Error ID: " + errorCode));
        }
        //The user could not be retreived from the NetskopeID table.
        else if (USER.user === null && USER.error === null) {
            const errorCode = await error_code_generator(new Error(), "1021")
            return(api.session.revoke("Backend Error. Error ID: " + errorCode));
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
            }
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
                const errorCode = await error_code_generator(new Error(), "1021")
                UPDATED = "Backend Error. Error ID: " + errorCode;
                return UPDATED;
              }
        }
        catch (error) {
            const errorCode = await error_code_generator(new Error(), "1021")
            UPDATED = "Backend Error. Error ID: " + errorCode;
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
            const errorCode = await error_code_generator(new Error(), "1021")
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    //If we detect an input to the form, we update the user's NetskopeID table object with the input.
    if (event.connection.name === "NetskopeID" && event.prompt?.fields?.hasOwnProperty("migration_policy")) {
        const dtn = Date.now();
        const dtu = (dtn-(dtn%1000))/1000;
        let migration_policy = event.prompt.fields.migration_policy;
        let update_object = {
            migration_policy: migration_policy,
            migration_policy_timestamp: dtu,
            mfd: false,
            blocked: false
        }
        if (migration_policy === false) {
            update_object.mfd = true;
            update_object.blocked = true;
        }

        let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
        if (UPDATED !== true) {
            const errorCode = await error_code_generator(new Error(), "1021")
            return(api.session.revoke("Backend Error. Error ID: " + errorCode));
        }
        if (migration_policy === false) {
            return(api.session.revoke("Account migration acknowledgement was not accepted."));
        }
        return;
    }
    else {
        return;
    }
}
```
