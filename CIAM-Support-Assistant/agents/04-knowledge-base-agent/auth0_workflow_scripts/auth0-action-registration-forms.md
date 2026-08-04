# Auth0 Action: Registration-Forms

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Registration-Forms

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 13bd6968-6bc7-42f4-9f2b-8738884ee0fb

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
                let errorCode = await error_code_generator(new Error(), "1041")
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1041")
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
                let errorCode = await error_code_generator(new Error(), "1041")
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1041")
            USER.error = "Backend Error. Error ID: " + errorCode;
            return USER;
        }
    }

    //Update a user object in the NetskopeID table.
    async function update_netskopeid_user(id, user) {
        const { DynamoDBClient, UpdateItemCommand } = require("@aws-sdk/client-dynamodb");
        const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");
        const { marshall } = require("@aws-sdk/util-dynamodb");

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
                let errorCode = await error_code_generator(new Error(), "1041")
                UPDATED = "Backend Error. Error ID: " + errorCode;
                return UPDATED;
            }
        }
        catch (error) {
            let errorCode = await error_code_generator(new Error(), "1041")
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
            let errorCode = await error_code_generator(new Error(), "1041")
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    //This functuion checks to see if the user already has a Netskope Community User.
    async function check_for_existing_community_user(USER, email) {
        if (!USER.hasOwnProperty("community_user") && (event.client?.metadata.entitlement??null) === "Community") {
            const axios = require('axios');

            async function get_community_token() {
                let options = {
                    method: "POST",
                    url: event.secrets.C_URL + "/oauth2/token?grant_type=client_credentials",
                    headers: { "Authorization": "Basic " + event.secrets.C_PWD}
                }

                const token = await axios(options)
                .then(response => {
                    if (response.status === 200) {
                        let toJson = response.data;
                        let token = "Bearer " + toJson.access_token.toString();
                        return token;
                    }
                })
                .catch(async error => {
                    let errorCode = await error_code_generator(new Error(), "1041");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return null;
                });
                return token;
            }

            async function clean_community_user(comm_user) {
                let obj = {
                    iam_a:"",
                    given_name:"",
                    family_name: "",
                    company_name: "",
                    job_title: "",
                    country_name: "",
                    state_province: ""
                };

                for (let index = 0; index < comm_user.profileFields.length; index++) {
                    let field = comm_user.profileFields[index];
                    switch (field.name) {
                        case "I am a..":
                            obj.iam_a = field.NormalizedValue.toLowerCase();
                            break;
                        case "First Name":
                            obj.given_name = field.NormalizedValue;
                            break;
                        case "Last Name":
                            obj.family_name = field.NormalizedValue;
                            break;
                        case "Company Name":
                            obj.company_name = field.NormalizedValue;
                            break;
                        case "Job Title":
                            obj.job_title = field.NormalizedValue;
                            break;
                        case "Country Name":
                            obj.country_name = field.NormalizedValue;
                            break;
                        case "State/Province":
                            obj.state_province = field.NormalizedValue;
                            break;
                        case "Topics of Interest…":
                            obj.topics_of_interest = Array.isArray(field.NormalizedValue) ? field.NormalizedValue : [field.NormalizedValue];
                            break;
                        default:
                            break;
                    }
                }

                obj.iam_a = obj.iam_a.toLowerCase().replace("g/\s+/", "_");
                obj.topics_of_interest = obj.topics_of_interest.map( topic => topic.toLowerCase().replaceAll(" ", "_"));
                return obj;
            }

            const token = await get_community_token();
            if (token !== null) {
                let options = {
                    method: "GET",
                    url: event.secrets.C_URL + "/user/email/" + encodeURIComponent(email),
                    headers: {"Content-Type": "application/json", "Authorization": token}
                }

                const community_fields = await axios(options)
                .then(async response => {
                    if (response.status === 200) {
                        let comm_user = response.data;
                        console.log(comm_user)
                        let obj = await clean_community_user(comm_user);
                        let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), obj);
                        if (UPDATED !== true) {
                            let errorCode = await error_code_generator(new Error(), "1041");
                            console.error("Backend Error. Error ID: " + errorCode);
                            return null;
                        }
                        else {
                            return obj;
                        }
                    }
                    else {
                        let errorCode = await error_code_generator(new Error(), "1041");
                        console.error("Backend Error. Error ID: " + errorCode);
                        return null;
                    }
                })
                .catch(async error => {
                    let errorCode = await error_code_generator(new Error(), "1041");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return null;
                })
                return community_fields;
            }
            else {
                let errorCode = await error_code_generator(new Error(), "1041");
                console.error("Backend Error. Error ID: " + errorCode);
                return null;
            }
        }
        else {
            return;
        }
    }
  
    if (event.connection.name === "NetskopeID") {
        let USER = await get_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id));
        //const FORM_ID = event.secrets.form_id;
        const FORM_ID_NAME = event.secrets.form_id_name;
        //const FORM_ID_ADD = event.secrets.form_id_add;
        const FORM_COMMUNITY_PENDING_USER_ID = event.secrets.form_community;

        if (USER.user !== null) {
            USER = USER.user;
            //Check for an existing Community user if the login is directed to Community and the user does not already have community_user set.
            if ((event.client?.metadata.entitlement??null) === "Community" && !USER.hasOwnProperty("community_user")) {
                let community_fields = await check_for_existing_community_user(USER, event.user.email);
                console.log(community_fields);
                if (community_fields !== null && Object.keys(community_fields).length > 0) {
                    //let update_object = {}
                    USER.iam_a = community_fields.iam_a;
                    //update_object.iam_a = community_fields.iam_a;
                    USER.given_name = community_fields.given_name;
                    //update_object.given_name = community_fields.given_name;
                    USER.family_name = community_fields.family_name;
                    //update_object.family_name = community_fields.family_name;
                    USER.company_name = community_fields.company_name;
                    //update_object.company_name = community_fields.company_name;
                    USER.job_title = community_fields.job_title;
                    //update_object.job_title = community_fields.job_title;
                    USER.country_name = community_fields.country_name;
                    //update_object.country_name = community_fields.country_name;
                    USER.state_province = community_fields.state_province;
                    //update_object.state_province = community_fields.state_province;
                    USER.topics_of_interest = community_fields.topics_of_interest;
                    //update_object.topics_of_interest = community_fields.topics_of_interest;

                    //let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
                    //if (UPDATED !== true) {
                    //    let errorCode = await error_code_generator(new Error(), "1041");
                    //    console.error("Backend Error. Error ID: " + errorCode);
                    //}
                }
            }
            //Render the full sign-up form if a user's COmmunity account was not found.
            if ((event.client?.metadata.entitlement??null) === "Community" && (!USER.iam_a || !USER.company_name)) {
                api.prompt.render(FORM_COMMUNITY_PENDING_USER_ID);
            }
            //Render the name form if the user does not have a given_name or family_name.
            else if (!USER.given_name || !USER.family_name) {
                api.prompt.render(FORM_ID_NAME);
            }
        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1041");
            console.error("Backend Error. Error ID: " + errorCode);
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1041");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }
    else {
        return;
    }
}

/**
* Handler that will be invoked when this action is resuming after an external redirect. If your
* onExecutePostLogin function does not perform a redirect, this function can be safely ignored.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onContinuePostLogin = async (event, api) => {
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
                let errorCode = await error_code_generator(new Error(), "1041");
                UPDATED = "Backend Error. Error ID: " + errorCode;
                return UPDATED;
            }
        }
        catch (error) {
            let errorCode = await error_code_generator(new Error(), "1041");
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
            let errorCode = await error_code_generator(new Error(), "1041");
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    //Basic input sanitizing
    async function sanatizeInput(data, typeS){
        if (typeS === "NAME") {
            if (typeof data !== "string") return "";
            let input = data.trim().replace(/\s+/g, " ").normalize("NFC");
            if (!/^[\p{L} '.-]+$/u.test(input)) {
                return "";
            }
            return input;
        }
        else if (typeS === "LOCATION") {
            if (typeof data !== "string") return "";
            let input = data.trim().replace(/\s+/g, " ").normalize("NFC");
            if (!/^[\p{L} '.,&()-]+$/u.test(input)) {
                return "";
            }
            return input;
        }
        else if (typeS === "OTHER") {
            if (typeof data !== "string") return "";
            let input = data.trim().replace(/\s+/g, " ").normalize("NFC");
            if (!/^[\p{L} '.,&()\d_-]+$/u.test(input)) {
                return "";
            }
            return input;
        }
    }

    //If we detect an input to the form, we update the user's NetskopeID table object with the input.
    if (event.connection.name === "NetskopeID" && (event.prompt?.id === event.secrets.form_id_name || event.prompt?.id === event.secrets.form_community)) {
        let update_object = {};

        if (event.prompt.id === event.secrets.form_id_name && event.prompt.fields?.hasOwnProperty("given_name") && event.prompt.fields?.hasOwnProperty("family_name")) {
            let sanatizeFirstName = await sanatizeInput(event.prompt.fields.given_name, "NAME");
            let sanatizeLastName = await sanatizeInput(event.prompt.fields.family_name, "NAME");
            update_object = {
                given_name: sanatizeFirstName??"",
                family_name: sanatizeLastName??"",
                name: `${sanatizeFirstName??""} ${sanatizeLastName??""}`
            };
            if (update_object.name === " ") {
                update_object.name = event.user.email;
            }
            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1041");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            else {
                return;
            }
        }
        else if (event.prompt.id === event.secrets.form_community && event.prompt.fields?.hasOwnProperty("iam_a") && event.prompt.fields?.hasOwnProperty("topics_of_interest")) {
            let sanatizeFirstName = await sanatizeInput(event.prompt.fields.given_name, "NAME");
            let sanatizeLastName = await sanatizeInput(event.prompt.fields.family_name, "NAME");
            let sanatizeCompanyName = await sanatizeInput(event.prompt.fields.company_name, "OTHER");
            let sanatizeJobTitle = await sanatizeInput(event.prompt.fields.job_title, "OTHER");
            let sanatizeCountryName = await sanatizeInput(event.prompt.fields.country_name, "LOCATION");
            let sanatizeStateProvince = await sanatizeInput(event.prompt.fields.state_province, "LOCATION");

            update_object = {
                given_name: sanatizeFirstName??"",
                family_name: sanatizeLastName??"",
                name: (sanatizeFirstName??"") + " " + (sanatizeLastName??""),
                company_name: sanatizeCompanyName??"",
                job_title: sanatizeJobTitle??"",
                country_name: sanatizeCountryName??"",
                state_province: sanatizeStateProvince??"",
                iam_a: event.prompt.fields.iam_a??"",
                topics_of_interest: event.prompt.fields.topics_of_interest??[],
                pending_community_user: true
            };
            if (update_object.name === " " || update_object.name === "") {
                update_object.name = event.user.email;
            }
            api.user.setAppMetadata("pending_community_user", true);
            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1041");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            else {
                return;
            }
        }
    }
    else {
        return;
    }
}

```
