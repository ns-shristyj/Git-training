# Auth0 Action: Federated-User-Deletion-Sync

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Federated-User-Deletion-Sync

- **Trigger(s):** event-stream
- **Status:** built
- **Action ID:** 61f0fd55-ee8a-4b9b-b717-c7716d2d4074

**Script:**
```javascript
/**
* Handler to be executed while processing events in an Event Stream.
* @param {Event} event - Details about the incoming event.
* @param {EventStreamAPI} api - Methods and utilities to define event stream processing.
*/
exports.onExecuteEventStream = async (event, api) => {
    // Removes a federated user's profile from the NetskopeID table when the user is
    // deleted in Auth0. Auth0 deletion does not cascade to the external DB, so this
    // Event Stream Action reacts to user.deleted and deletes the matching DB row.
    //
    // Scope: federated (non-NetskopeID) users only. The DB row is keyed on the uuid
    // we stamp into app_metadata.nsid_user_id at first federated login (see
    // sync_federated_user_to_netskopeid in 7-NetskopeID-Sync-2.js). Native NetskopeID
    // users are keyed differently and never carry nsid_user_id, so its absence means
    // there is no federated row to remove and we no-op.
    //
    // This Action only deletes from DynamoDB (never writes back to Auth0), so it
    // cannot re-trigger itself.

    // Native DB connection — never act on it here.
    const NATIVE_CONNECTION = "NetskopeID";

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

    //Delete a user object from the NetskopeID table.
    //Mirrors the STS assume-role + DynamoDB flow in 7-NetskopeID-Sync-2.js so behavior/secrets stay identical.
    async function delete_netskopeid_user(id) {
        const { DynamoDBClient, DeleteItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");
        const { marshall } = require("@aws-sdk/util-dynamodb");

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
                return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1091");
            }
        }
        catch (error) {
            return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1091");
        }

        const client = new DynamoDBClient({
            region: event.secrets.REG,
            credentials: {
                accessKeyId: stsResponse.Credentials.AccessKeyId,
                secretAccessKey: stsResponse.Credentials.SecretAccessKey,
                sessionToken: stsResponse.Credentials.SessionToken
            }
        });

        // DeleteItem is idempotent: a missing key still returns 200, so a duplicate
        // delete (or an already-cleaned row) is a harmless no-op.
        const command = new DeleteItemCommand({
            TableName: event.secrets.TN,
            Key: marshall({ user_id: id })
        });
        const response = await client.send(command);
        if (response.$metadata.hasOwnProperty("httpStatusCode") && response.$metadata.httpStatusCode === 200) {
            return true;
        }
        return "Backend Error. Error ID: " + await error_code_generator(new Error(), "1091");
    }

    //Remove the federated user's NetskopeID table row on Auth0 deletion.
    async function delete_federated_user_from_db() {
        const user = event.message?.data?.object;
        if (!user) {
            return;
        }

        const app_metadata = user.app_metadata ?? {};

        // The DB row is keyed on the uuid stamped at first federated login. Only
        // federated users carry nsid_user_id; without it there is no row to delete.
        const nsid_user_id = app_metadata.nsid_user_id;
        if (!nsid_user_id) {
            return;
        }

        // Belt-and-suspenders: never act on the native connection even if a row
        // somehow carried an nsid_user_id. Deletion payloads may omit identities,
        // in which case connection is undefined and we proceed (nsid_user_id has
        // already established this is a federated row).
        const connection = user.identities?.[0]?.connection;
        if (connection === NATIVE_CONNECTION) {
            return;
        }

        const DELETED = await delete_netskopeid_user(nsid_user_id);
        if (DELETED !== true) {
            let errorCode = await error_code_generator(new Error(), "1091");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    console.log(JSON.stringify(event.message));
    await delete_federated_user_from_db();
    return;
};

```

## Rules (Legacy)

_No rules found — tenant likely uses Actions exclusively._
