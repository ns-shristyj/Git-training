# Auth0 Action: Federated-User-To-NetskopeID-Sync

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Federated-User-To-NetskopeID-Sync

- **Trigger(s):** event-stream
- **Status:** built
- **Action ID:** e919aaf1-cb7b-4774-9e3c-fec404e9452f

**Script:**
```javascript
/**
* Handler to be executed while processing events in an Event Stream.
* @param {Event} event - Details about the incoming event.
* @param {EventStreamAPI} api - Methods and utilities to define event stream processing.
*/
exports.onExecuteEventStream = async (event, api) => {
    // Keeps the NetskopeID table in sync when an admin changes a federated user's
    // entitlements/permissions in Auth0. Those two fields are admin-managed and the
    // DB is projected to session at login (Actions 6 & 7), so an Auth0-side edit only
    // reaches the DB through this Event Stream Action reacting to user.updated.
    // roles/birthright are Salesforce-derived at login and are intentionally NOT
    // written here. Runs for every update except the connections handled elsewhere.
    // This Action only writes to DynamoDB (never back to Auth0), so it cannot
    // re-trigger itself.

    // Connections handled elsewhere; never synced from here.
    //   NetskopeID   -> native DB connection (synced at login by Actions 6 & 7)
    //   NSKP-Preview -> internal/group-based connection, managed separately
    // Sandbox uses "NSKP-Preview"; replace with "Netskope" in production (matches
    // GROUP_BASED_CONNECTION in 7-NetskopeID-Sync-2.js).
    const EXCLUDED_CONNECTIONS = ["NetskopeID"];
    //const EXCLUDED_CONNECTIONS = ["NetskopeID", "NSKP-Preview"];

    //Generates error codes based on the error stack trace. (kept consistent with the Sync Actions)
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
    //Mirrors update_netskopeid_user() in 7-NetskopeID-Sync-2.js so behavior/secrets stay identical.
    async function update_netskopeid_user(id, user) {
        const { DynamoDBClient, UpdateItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");
        const { marshall } = require("@aws-sdk/util-dynamodb");

        function buildUpdateParams(tableName, key, updateObject) {
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
                Key: marshall({ user_id: key }),
                UpdateExpression: `SET ${UpdateExpressions.join(", ")}`,
                ExpressionAttributeNames,
                ExpressionAttributeValues: marshall(ExpressionAttributeValues, { removeUndefinedValues: true }),
                ReturnValues: "ALL_NEW"
            };
        }

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
                return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1081");
            }
        }
        catch (error) {
            return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1081");
        }

        const client = new DynamoDBClient({
            region: event.secrets.REG,
            credentials: {
                accessKeyId: stsResponse.Credentials.AccessKeyId,
                secretAccessKey: stsResponse.Credentials.SecretAccessKey,
                sessionToken: stsResponse.Credentials.SessionToken
            }
        });

        const command = new UpdateItemCommand(buildUpdateParams(event.secrets.TN, id, user));
        const response = await client.send(command);
        if (response.$metadata.hasOwnProperty("httpStatusCode") && response.$metadata.httpStatusCode === 200) {
            return true;
        }
        return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1081");
    }

    //Push the user's current app_metadata fields into the NetskopeID table for federated users.
    async function sync_federated_app_metadata_to_db() {
        const user = event.message?.data?.object;
        if (!user) {
            return;
        }

        const app_metadata = user.app_metadata ?? {};

        // Skip native/internal connections; only external federated users sync from here.
        const connection = user.identities?.[0]?.connection;
        if (!connection || EXCLUDED_CONNECTIONS.includes(connection)) {
            return;
        }

        // The DB row is keyed on the uuid we stamp at first federated login
        // (see sync_federated_user_to_netskopeid in 7-NetskopeID-Sync-2.js). No
        // nsid_user_id means there's no row yet — the login Action creates it,
        // so there's nothing to update here.
        const nsid_user_id = app_metadata.nsid_user_id;
        if (!nsid_user_id) {
            return;
        }

        // Auth0 app_metadata is authoritative only for entitlements/permissions
        // (admin-managed). roles/birthright are Salesforce-derived by the login
        // Action (set_birthright_access) and must never be written back from here.
        // Guard each so a missing/non-array value never blanks good DB data.
        const updateObject = {};
        if (Array.isArray(app_metadata.entitlements)) updateObject.entitlements = app_metadata.entitlements;
        if (Array.isArray(app_metadata.permissions))  updateObject.permissions  = app_metadata.permissions;

        if (Object.keys(updateObject).length === 0) {
            return;
        }

        const UPDATED = await update_netskopeid_user(nsid_user_id, updateObject);
        if (UPDATED !== true) {
            let errorCode = await error_code_generator(new Error(), "1081");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    //console.log(JSON.stringify(event.message));
    await sync_federated_app_metadata_to_db();
    return;
};
```
