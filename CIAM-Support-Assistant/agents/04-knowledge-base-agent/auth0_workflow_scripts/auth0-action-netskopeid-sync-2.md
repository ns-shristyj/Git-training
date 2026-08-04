# Auth0 Action: NetskopeID-Sync-2

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### NetskopeID-Sync-2

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** bb237d59-6ef7-420e-881a-345c8d0bc3a2

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
//onExecutePostLogin = async (event, api) => {
exports.onExecutePostLogin = async (event, api) => {
    const { DynamoDBClient, GetItemCommand, UpdateItemCommand } = require("@aws-sdk/client-dynamodb");
    const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");
    const { marshall,unmarshall } = require("@aws-sdk/util-dynamodb");
	const { v4: uuidv4 } = require("uuid");

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

    async function validate_sf_data(sf_data) {
        let isValid = false;

        if (typeof sf_data !== "string") {
            return isValid;
        }

        // Basic SFDC object regex validation
        const sfdcObjectRegex = /^[A-Za-z0-9\-]+$/;
        if (!sfdcObjectRegex.test(sf_data)) {
            return isValid;
        }

        isValid = true;
        return isValid;
    }

    //This function will sanitize and validate provided email addresses.
    async function sanitizeEmail(email) {
        /**
         * @type {{email: string|null, error: string|null}}
         */
        let EMAIL_CHECK = {
            email: null,
            error: null
        };

        // Check if email is provided
        if (!email) {
            EMAIL_CHECK.error = "Email is required";
            return EMAIL_CHECK;
        }
    
        // Check if email is a string
        if (typeof email !== "string") {
            EMAIL_CHECK.error = "Invalid email format";
            return EMAIL_CHECK;
        }
    
        // Trim whitespace and convert to lowercase
        const sanitized = email.trim().toLowerCase();
    
        // Check if email is empty after trimming
        if (!sanitized) {
            EMAIL_CHECK.error = "Email is required";
            return EMAIL_CHECK;
        }
    
        // Check for common malicious patterns
        const maliciousPatterns = [
            /<script/i,
            /javascript:/i,
            /onclick/i,
            /onerror/i,
            /<iframe/i,
            /\x00/g, // null bytes
            /\r\n/g, // CRLF injection
            /\"/g
        ];
    
        for (const pattern of maliciousPatterns) {
            if (pattern.test(sanitized)) {
                EMAIL_CHECK.error = "Invalid email format";
                return EMAIL_CHECK;
            }
        }

        // Basic email regex validation
        const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
        if (!emailRegex.test(sanitized)) {
            EMAIL_CHECK.error = "Invalid email format";
            return EMAIL_CHECK;
        }
    
        // Check length constraints
        if (sanitized.length > 255) {
            EMAIL_CHECK.error = "Invalid email length";
            return EMAIL_CHECK;
        }
    
        const [localPart, domain] = sanitized.split("@");
    
        if (localPart.length > 64) {
            EMAIL_CHECK.error = "Invalid email length";
            return EMAIL_CHECK;
        }
    
        if (domain.length > 254) {
            EMAIL_CHECK.error = "Invalid email length";
            return EMAIL_CHECK;
        }
    
        EMAIL_CHECK.email = sanitized;
        EMAIL_CHECK.error = null;
        return EMAIL_CHECK;
    }

    //Retrive the user's profile from the NetskopeID table.
    async function get_netskopeid_user(id) {

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
                let errorCode = await error_code_generator(new Error(), "1061");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1061");
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
                USER.user = unmarshall(response.Item,{removeUndefinedValues: true});
                return USER;
            }
            else {
                USER.user = null;
                let errorCode = await error_code_generator(new Error(), "1061");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1061");
            USER.error = "Backend Error. Error ID: " + errorCode;
            return USER;
        }
    }

    //Update a user object in the NetskopeID table.
    async function update_netskopeid_user(id, user) {
        async function buildUpdateParams(tableName, key, updateObject) {
            const ExpressionAttributeNames = {};
            const ExpressionAttributeValues = {};
            const UpdateExpressions = [];

            for (const [field, value] of Object.entries(updateObject)) {
                // Skip undefined values: marshall() with removeUndefinedValues
                // would strip them from ExpressionAttributeValues while the
                // UpdateExpression still references them, causing DynamoDB's
                // "expression attribute value ... is not defined" error.
                if (value === undefined) {
                    continue;
                }
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
                ExpressionAttributeValues: marshall(ExpressionAttributeValues,{removeUndefinedValues: true}),
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
                    let errorCode = await error_code_generator(new Error(), "1061");
                    UPDATED = "Backend Error. Error ID: " + errorCode;
                    return UPDATED;
                }
        }
        catch (error) {
            let errorCode = await error_code_generator(new Error(), "1061");
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
            let errorCode = await error_code_generator(new Error(), "1061");
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    //Retrieve a user's Netskope Community account details.
    async function community_provisioning() {
        const axios = require("axios");
        const { v4: uuidv4 } = require("uuid");

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
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return null;
            });
            return token;
        }

        //Create a Netskope Community user.
        async function create_community_user(USER, token) {
            let options = {};

            try {
                //No Contact information found, create pending approval user.
                if (USER.hasOwnProperty("sf_contact") && Object.keys(USER.sf_contact).length === 0) {
                    let uname = USER.email.split("@")[0]+"-"+uuidv4().split("-")[0];
                    if (uname.length >= 30) {
                        let u = uuidv4();
                        uname = u.split("-")[0] + "-" + u.split("-")[1] + "-" + u.split("-")[2];
                    }
                    options = {
                        method: "POST",
                        url: event.secrets.C_URL + "/user/register",
                        headers: {"Authorization": token, "Content-Type": "application/json"},
                        data: {
                            data: {
                                email: USER.email,
                                password: uuidv4(),
                                username: uname,
                                user_role: ["roles.requires-approval"],
                                profile_field: {
                                    3: USER.state_province,
                                    4: USER.country_name,
                                    5: USER.company_name,
                                    6: USER.job_title,
                                    8: USER.iam_a,
                                    9: USER.given_name,
                                    10: USER.family_name,
                                    11: USER.topics_of_interest
                                }
                            }
                        }
                    }
                }
                //Contactn information found, create fully provisioned user.
                else {
                    let uname = USER.email.split("@")[0]+"-"+uuidv4().split("-")[0];
                    if (uname.length >= 30) {
                        let u = uuidv4();
                        uname = u.split("-")[0] + "-" + u.split("-")[1] + "-" + u.split("-")[2];
                    }
                    options = {
                        method: "POST",
                        url: event.secrets.C_URL + "/user/register",
                        headers: {"Authorization": token, "Content-Type": "application/json"},
                        data: {
                            data: {
                                email: USER.email,
                                password: uuidv4(),
                                username: uname,
                                user_role: ["roles.registered"],
                                profile_field: {
                                    3: USER.state_province,
                                    4: USER.country_name,
                                    5: USER.company_name,
                                    6: USER.job_title,
                                    8: USER.iam_a,
                                    9: USER.given_name,
                                    10: USER.family_name,
                                    11: USER.topics_of_interest
                                }
                            }
                        }
                    }
                }
            }
            catch (err) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);

                let update_object = {
                    community_user:{},
                    pending_community_user:true
                };
                api.user.setAppMetadata("pending_community_user", true);

                let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
                if (UPDATED !== true) {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return;
                }
                else {
                    return;
                }
            }


            //Send request to create community user.
            const CREATED = await axios(options)
            .then(async response => {
                if (response.status === 200) {
                    //User created successfully.
                    let CREATED = {
                        user: {
                            community_user: {
                                userid: response.data.user.userid,
                                roles: options.data.data.user_role
                            }
                        },
                        status: true
                    }
                    return CREATED;
                }
                else {
                    //Error occurred during creation.
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    let CREATED = {
                        user: {
                            community_user: {
                                userid: response.data.user.userid,
                                roles: options.data.data.user_role
                            }
                        },
                        status: false
                    }
                    return CREATED;
                }
            })
            .catch(async error => {
                //Error occurred during creation.
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                let CREATED = {
                    user: {
                        community_user: {}
                    },
                    status: false
                }
                return CREATED;
            })

            let update_object = {};

            //No Contact information found, user is now pending approval.
            if (CREATED.status === true && USER.hasOwnProperty("sf_contact") && Object.keys(USER.sf_contact).length === 0) {
                update_object = {
                    community_user:CREATED.user.community_user,
                    pending_community_approval:true,
                    pending_community_user:false
                };
                api.user.setAppMetadata("pending_community_approval", true);
                api.user.setAppMetadata("pending_community_user", false);
            }
            //Contact information found, user is fully provisioned.
            else if (CREATED.status === true && USER.hasOwnProperty("sf_contact") && Object.keys(USER.sf_contact).length >= 1) {
                update_object = {
                    community_user:CREATED.user.community_user,
                    pending_community_approval:false,
                    pending_community_user:false
                };
                api.user.setAppMetadata("pending_community_approval", false);
                api.user.setAppMetadata("pending_community_user", false);
            }
            //Error occurred during creation.
            else if (CREATED.status !== true) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                update_object = {
                    community_user:CREATED.user.community_user,
                    pending_community_user:true
                };
                api.user.setAppMetadata("pending_community_user", true);
            }

            //Update NetskopeID table object with community_user details.
            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
            else {
                return;
            }
        }

        if ((event.client?.metadata.entitlement??null) === "Community") {
            
            let USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

            if (USER.user !== null) {
                USER = USER.user;
            
                if (!USER.hasOwnProperty("community_user") || (USER.hasOwnProperty("community_user") && Object.keys(USER.community_user).length === 0)) {
                    
                    const token = await get_community_token();
                    
                    if (token !== null) {
                        let email = "";

                        let eventEmail = await sanitizeEmail(event.user.email??"");

                        if (eventEmail.email !== null && eventEmail.error ===  null) {
                            email = eventEmail.email;
                        }
                        else {
                            let errorCode = await error_code_generator(new Error(), "1061");
                            console.error("Backend Error. Error ID: " + errorCode);
                            email = "";
                        }

                        let options = {
                            method: "GET",
                            url: event.secrets.C_URL + "/user/email/" + encodeURIComponent(email),
                            headers: {"Content-Type": "application/json", "Authorization": token}
                        }
                        const community_user = await axios(options)
                        .then(async response => {
                            if (response.status === 200) {
                                try {
                                    let roles = [];
                                    for (let i = 0; i < response.data.roles.length; i++) {
                                        roles.push(response.data.roles[i].auth_item.name);
                                    }
                                    let user = {
                                        community_user: {
                                            userid: response.data.userid,
                                            roles: roles
                                        },
                                        pending_community_user: false
                                    }
                                    api.user.setAppMetadata("pending_community_user",false);
                                    return user;
                                }
                                catch (err) {
                                    let errorCode = await error_code_generator(new Error(), "1061");
                                    console.error("Backend Error. Error ID: " + errorCode);
                                    let user = {
                                        community_user: {
                                            userid: response.data.userid,
                                            roles: response.data.roles
                                        },
                                        pending_community_user: false
                                    }
                                    api.user.setAppMetadata("pending_community_user",false);
                                    return user;
                                }
                            }
                            else if (response.status === 404) {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                                await create_community_user(USER, token);
                                return null;
                            }
                            else {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                                let user = {
                                    community_user: {},
                                    pending_community_user: true
                                }
                                api.user.setAppMetadata("pending_community_user",true);
                                return user;
                            }
                        })
                        .catch(async error => {
                            if (error.response?.status === 404) {
                                await create_community_user(USER, token);
                                return null;
                            }
                            else {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                                let user = {
                                    community_user: {},
                                    pending_community_user: true
                                }
                                api.user.setAppMetadata("pending_community_user",true);
                                return user;
                            }
                        })

                        if (community_user !== null) {
                            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), community_user);
                            if (UPDATED !== true) {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                            }
                        }
                        else {
                            return;
                        }
                    }
                    else {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                        let user = {
                            community_user: {},
                            pending_community_user: true
                        }
                        api.user.setAppMetadata("pending_community_user",true);

                        let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), user);
                        if (UPDATED !== true) {
                            let errorCode = await error_code_generator(new Error(), "1061");
                            console.error("Backend Error. Error ID: " + errorCode);
                        }
                    }
                }

                if (USER.hasOwnProperty("community_user") && Object.keys(USER.community_user).length > 0) {
                    if (USER.community_user.hasOwnProperty("roles") && Array.isArray(USER.community_user.roles) && USER.community_user.roles.length > 0) {
                        if (USER.community_user.roles[0].hasOwnProperty("auth_item")) {
                            const roles = [];
                            for (let i = 0; i < USER.community_user.roles.length; i++) {
                                roles.push(USER.community_user.roles[i].auth_item.name);
                            }
                            let user = {
                                community_user: {
                                    userid: USER.community_user.userid,
                                    roles: roles
                                }
                            }
                            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), user);
                            if (UPDATED !== true) {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                            }
                            if (user.community_user.roles.includes("roles.requires-approval") && !event.user.app_metadata.hasOwnProperty("pending_community_approval")) {
                                api.user.setAppMetadata("pending_community_approval",true);
                            }
                            return;
                        }
                        return;
                    }
                    return;
                }
                else {
                    return;
                }
            }
            else if (USER.error !== null) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
            else {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
        }
        else {
            return;
        }
    }

    //Check the approval status of a Community user.
    async function check_community_user_approval_status() {
        const axios = require("axios");

        async function get_community_token() {
            var options = {
                method: "POST",
                url: event.secrets.C_URL + "/oauth2/token?grant_type=client_credentials",
                headers: { "Authorization": "Basic " + event.secrets.C_PWD}
            }
            const token = await axios(options)
            .then(response => {
                if (response.status === 200) {
                    var toJson = response.data;
                    var token = "Bearer " + toJson.access_token.toString();
                    return token;
                }
            })
            .catch(async error => {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return null;
            });
            return token;
        }

        async function get_community_user(USER) {
            const token = await get_community_token();
            if (token !==  null) {
                var options = {
                    method: "GET",
                    url: event.secrets.C_URL + "/user/" + USER.community_user.userid + "/roles",
                    headers: {"Authorization": token, "Content-Type": "application/json"}
                }
                const communityUserRoles = await axios(options)
                .then(async response => {
                    if (response.status === 200) {
                        var roles = response.data.roles;
                        return roles;
                    }
                    else {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                        return null;
                    }
                })
                .catch(async error => {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return null;
                })
                return communityUserRoles;
            }
            else {
                return null;
            }
        }

        if ((event.client?.metadata.entitlement??null) === "Community") {
            
            let USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

            if (USER.user !== null) {
                USER = USER.user;

                if (USER.hasOwnProperty("community_user") && USER.community_user.hasOwnProperty("userid")) {
                    var community_user_roles = await get_community_user(USER);
                    var update_object = {};
                    
                    if (community_user_roles !== null && community_user_roles.includes("roles.requires-approval")) {
                        update_object = {pending_community_approval:true};
                        api.user.setAppMetadata("pending_community_approval", true);
                    }
                    else if (community_user_roles !== null && community_user_roles.includes("roles.registered")) {
                        update_object = {pending_community_approval:false};
                        api.user.setAppMetadata("pending_community_approval", false);
                    }
                    else if (community_user_roles !== null && !community_user_roles.includes("roles.requires-approval") && !community_user_roles.includes("roles.registered")) {
                        update_object = {pending_community_approval:true};
                        api.user.setAppMetadata("pending_community_approval", true);
                    }
                    else {
                        update_object = {pending_community_approval:true};
                        api.user.setAppMetadata("pending_community_approval", true);
                    }
                    
                    var UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
                    if (UPDATED !== true) {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                    else {
                        return;
                    }
                }
            }
            else if (USER.error !== null) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
            else {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
        }
        else {
            return;
        }
    }

    //Create federated users within Impartner, if they don't already exist.
    async function create_impartner_user() {
        const axios = require("axios");
        try {
            if (event.connection.name !== "NetskopeID" && event.user.app_metadata['roles']?.includes('nskp-partner') && event.user.app_metadata?.federated === true && event.stats.logins_count <= 3) {
                await axios({
                    method: "get",
                    headers: {"Content-Type": "application/json"},
                    url: "https://stage.impartner.live/api/objects/v1/User",
                    params: {filter: "email='" + event.user.email + "'", fields: "email,id"},
                    auth: {username: event.secrets.impEmail, password: event.secrets.impPwd}
                })
                .then(async function(response) {
                    try {
                        let userCount = response.data.data.results.length;
                        if (userCount === 0) {
                            await axios({
                                method: "put",
                                headers: {"Content-Type": "application/json"},
                                url: "https://stage.impartner.live/api/objects/v1/User",
                                auth: {username: event.secrets.impEmail, password: event.secrets.impPwd},
                                data: {"Account": event.user.partner_id, "Email": event.user.email, "FirstName": event.user.given_name, "LastName": event.user.family_name, "Username": event.user.email, "Auth0_ID__cf": event.user.identities[0].provider +"|"+ event.user.identities[0].user_id}
                            })
                            .then(async function(response) {
                                try {
                                    if (response.data.success !== true) {
                                        let errorCode = await error_code_generator(new Error(), "1061");
                                        console.error("Backend Error. Error ID: " + errorCode);
                                    }
                                }
                                catch(error) {
                                    let errorCode = await error_code_generator(new Error(), "1061");
                                    console.error("Backend Error. Error ID: " + errorCode);
                                }
                            })
                            .catch(async function(error) {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                            })
                        }
                        else {
                            let errorCode = await error_code_generator(new Error(), "1061");
                            console.error("Backend Error. Error ID: " + errorCode);
                        }
                    }
                    catch(error){
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                })
                .catch(async function(error){
                    console.log(error)
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                })
            }
            else {
                console.log("WTH");
            }
        }
        catch(err){
          let errorCode = await error_code_generator(new Error(), "1061");
          console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    //Update the Auth0 ID within Impartner for a user.
    async function update_auth0id_within_impartner() {
        const axios = require("axios");
        if (event.user.app_metadata['roles']?.includes('nskp-partner') && (event.user.app_metadata.sendId === true || event.user.app_metadata.send_id === true)) {
            await axios({
                method: "get",
                headers: {"Content-Type": "application/json"},
                url: "https://stage.impartner.live/api/objects/v1/User",
                params: {filter: "email='" + event.user.email + "'", fields: "email,id"},
                auth: {username: event.secrets.impEmail, password: event.secrets.impPwd}
            })
            .then(async function(response) {
                let user = response.data.data.results[0];
                try {
                    if (user.email === event.user.email) {
                        if(event.user.identities[0].provider === "auth0") {
                            await axios({
                                method: "patch",
                                headers: {"Content-Type": "application/json"},
                                url: "https://stage.impartner.live/api/objects/v1/User/" + String(user.id),
                                auth: {username: event.secrets.impEmail, password: event.secrets.impPwd},
                                data: {"id": user.id, "Auth0_ID__cf": event.user.identities[0].user_id}
                            })
                            .then( async function(response) {
                                try {
                                    if (response.data.success === true) {
                                        if (event.connection.name === "NetskopeID") {
                                            let obj = {
                                                sendId: false,
                                                send_id: false
                                            }
                                            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), obj);
                                            if (UPDATED !== true) {
                                                let errorCode = await error_code_generator(new Error(), "1061");
                                                console.error("Backend Error. Error ID: " + errorCode);
                                            }
                                        }
                                        api.user.setAppMetadata("sendId", false);
                                        api.user.setAppMetadata("send_id", false);
                                        return;
                                    }
                                    else {
                                        let errorCode = await error_code_generator(new Error(), "1061");
                                        console.error("Backend Error. Error ID: " + errorCode);
                                    }
                                }
                                catch(error) {
                                    let errorCode = await error_code_generator(new Error(), "1061");
                                    console.error("Backend Error. Error ID: " + errorCode);
                                }
                            })
                            .catch( async function(error){
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                            })
                        }
                        else {
                            await axios({
                                method: "patch",
                                headers: {"Content-Type": "application/json"},
                                url: "https://stage.impartner.live/api/objects/v1/User/" + String(user.id),
                                auth: {username: event.secrets.impEmail, password: event.secrets.impPwd},
                                data: {"id": user.id, "Auth0_ID__cf": event.user.identities[0].provider+"|"+event.user.identities[0].user_id}
                            })
                            .then( async function(response) {
                                try {
                                    if (response.data.success === true) {
                                        api.user.setAppMetadata("sendId", false)
                                        api.user.setAppMetadata("send_id", false)
                                        return;
                                    }
                                    else {
                                        let errorCode = await error_code_generator(new Error(), "1061");
                                        console.error("Backend Error. Error ID: " + errorCode);
                                    }
                                }
                                catch(error) {
                                    let errorCode = await error_code_generator(new Error(), "1061");
                                    console.error("Backend Error. Error ID: " + errorCode);
                                }
                            })
                            .catch(async function(error) {
                                let errorCode = await error_code_generator(new Error(), "1061");
                                console.error("Backend Error. Error ID: " + errorCode);
                            })
                        }
                    }
                    else {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                }
                catch(error) {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                }
            })
            .catch(async function(error) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
            })
        }
        else {
          return;
        }
    }

    //Update birthright access based on Salesforce Account Status and Tenant Requests.
    async function set_birthright_access(USER) {
        // USER.user_id is the DB primary key for both NetskopeID (split id) and
        // federated (uuid) users; deriving the key from event.user.user_id would
        // target the wrong row for federated users.
        const dbKey = USER.user_id;

        // Group-based birthright (Action 6) owns this connection, so it is excluded
        // here. Salesforce-based birthright applies to NetskopeID and every other
        // federated connection. Sandbox uses "NSKP-Preview"; replace with "Netskope"
        // in production.
        const GROUP_BASED_CONNECTION = "NSKP-Preview";
        const birthright_eligible = event.connection.name !== GROUP_BASED_CONNECTION;

        // Shared by every birthright branch below: build a DB update payload from
        // the user's current profile fields plus the supplied roles/birthright.
        function build_hourly_updates(roles, birthright) {
            const u = { last_sync: dtu, roles, birthright };
            if (event.user.user_metadata.hasOwnProperty("given_name")) {
                u.given_name = event.user.user_metadata.given_name;
            }
            if (event.user.user_metadata.hasOwnProperty("family_name")) {
                u.family_name = event.user.user_metadata.family_name;
            }
            if (event.user.user_metadata.hasOwnProperty("name")) {
                u.name = event.user.user_metadata.name ?? "";
                if (u.name === "") {
                    u.name = event.user.email;
                }
            }
            u.entitlements = event.user.app_metadata.entitlements;
            u.permissions = event.user.app_metadata.permissions;
            return u;
        }

        // Persist a birthright decision: write the DB row and mirror
        // birthright/last_sync onto the session's app_metadata.
        async function apply_birthright(roles, birthright) {
            const UPDATED = await update_netskopeid_user(dbKey, build_hourly_updates(roles, birthright));
            if (UPDATED !== true) {
                const errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            api.user.setAppMetadata('birthright', birthright);
            api.user.setAppMetadata('last_sync', dtu);
        }

        //Provide birthright access for users.
        if ((birthright_eligible && USER.hasOwnProperty('sf_account') && USER.roles?.length === 0) || (birthright_eligible && USER.hasOwnProperty('sf_account') && (dtu - (event.user.app_metadata.last_sync??dtu-3601)) >= 3600)) {
            
            //Support Birthright Allowlist
            if (USER.sf_account.hasOwnProperty('Id') && USER.sf_account.Id !== "" && (USER.sf_account.Id === event.secrets.MS_ACC_ID || USER.sf_account.Id === event.secrets.NAU_ACC_ID)) {
                await apply_birthright(['nskp-integrator'], ['Support','Community','Academy','Notification','Dashboard']);
                return;
            }

            //Provide Customer birthright access.
            if (USER.sf_account.Account_Status__c !== "" && USER.sf_account.Account_Status__c === "Customer") {
                //console.log("Customer");
                await apply_birthright(['nskp-customer'], ['Support','Community','Academy','Notification','Dashboard']);
                return;
            }

            //Provide Prospect and Pending Partner birthright access.
            if (USER.sf_account.Account_Status__c !== "" && (USER.sf_account.Account_Status__c?.includes("Prospect") || USER.sf_account.Account_Status__c === "Pending Partner")) {
                //console.log("Prospect");
                //Prospect and Pending Partners with an Active Tenant also get Support access.
                let birthright = ['Community','Academy','Dashboard'];
                if (USER.hasOwnProperty('ns_tenants') && USER.ns_tenants.length >= 1) {
                    for (var i = 0; i < USER.ns_tenants.length; i++) {
                        if (USER.ns_tenants[i].Tenant_Provision_Status__c === "Active Tenant") {
                            birthright = ['Community','Academy','Support','Notification','Dashboard'];
                            break;
                        }
                    }
                }
                await apply_birthright(['nskp-prospect'], birthright);
                return;
            }

            //Provide Partner birthright access
            if ((USER.sf_account.Primary_Partner_Type__c === "MSP" || USER.sf_account.Secondary_Partner_Type__c === "MSP" || USER.sf_account.Tertiary_Partner_Type__c === "MSP") || (USER.sf_account.Primary_Partner_Type__c === "Service Provider/Telco" || USER.sf_account.Secondary_Partner_Type__c === "Service Provider/Telco" || USER.sf_account.Tertiary_Partner_Type__c === "Service Provider/Telco")) {
                //console.log("Partner with Support Access");
                var current_roles = USER.roles;
                current_roles.push('nskp-partner-msp');
                current_roles = [...new Set(current_roles)]
                if (current_roles.includes('nskp-prime') || event.user.app_metadata.roles?.includes('nskp-prime')) {
                    await apply_birthright(current_roles, ["Support","Community","Academy","Notification","Prime", "Partner","Dashboard"]);
                    return;
                }
                else {
                    await apply_birthright(current_roles, ['Support','Community','Academy','Notification', 'Partner','Dashboard']);
                    return;
                }
            }
            else if (USER.sf_account.Account_Status__c === "Partner" && USER.sf_account.Customer_Status__c?.includes("Customer")) {
                //console.log("Partner Customer");
                var current_roles = USER.roles;
                current_roles.push('nskp-customer');
                current_roles.push('nskp-partner');
                current_roles = [...new Set(current_roles)]
                if (current_roles.includes('nskp-prime') || event.user.app_metadata.roles?.includes('nskp-prime')) {
                    await apply_birthright(current_roles, ['Support','Community','Academy','Notification','Prime', 'Partner','Dashboard']);
                    return;
                }
                else {
                    await apply_birthright(current_roles, ['Support','Community','Academy','Notification', 'Partner','Dashboard']);
                    return;
                }
            }
            else if (USER.sf_account.Account_Status__c === "Partner" || event.user.app_metadata.roles?.includes("nskp-partner")) {
                //console.log("Partner");
                var current_roles = USER.roles;
                current_roles = [...new Set(current_roles)]
                if (current_roles.includes('nskp-prime') || event.user.app_metadata.roles?.includes('nskp-prime')) {
                    await apply_birthright(current_roles, ['Support','Community','Academy','Partner','Prime','Notification','Dashboard']);
                    return;
                }
                else {
                    await apply_birthright(current_roles, ['Support','Community','Academy','Partner','Notification','Dashboard']);
                    return;
                }
            }

            //Provide Churn birthright access
            if (USER.sf_account.Account_Status__c !== "" && USER.sf_account.Account_Status__c === "Churn") {
                //console.log("Churn");
                //Churned accounts with an Active Tenant keep customer-level access.
                let roles = ['nskp-individual'];
                let birthright = ['Community','Dashboard'];
                if (USER.hasOwnProperty('ns_tenants') && USER.ns_tenants.length >= 1) {
                    for (var i = 0; i < USER.ns_tenants.length; i++) {
                        if (USER.ns_tenants[i].Tenant_Provision_Status__c === "Active Tenant") {
                            roles = ['nskp-customer'];
                            birthright = ['Community','Academy','Support','Notification','Dashboard'];
                            break;
                        }
                    }
                }
                await apply_birthright(roles, birthright);
                return;
            }

            //Provide Quarantine/Out of Business birthright access
            if (USER.sf_account.Account_Status__c !== "" && USER.sf_account.Account_Status__c === "Quarantine/Out of Business") {
                //console.log("Quarantine/Out of Business");
                await apply_birthright(['nskp-individual'], ['Community','Dashboard']);
                return;
            }

            //Provide Individual birthright access.
            if (Object.keys(USER.sf_account).length === 0) {
                //console.log("Individual");
                await apply_birthright(['nskp-individual'], ['Community','Dashboard']);
                return;
            }
            return;
        }
        else {
            return;
        }
    }

    //Sync federated users with NetskopeID table and create an entry if one does not exist.
    //This is to ensure that federated users can be properly enriched with Salesforce data and have the necessary fields for birthright and entitlement management.
    async function sync_federated_user_to_netskopeid() {
        const axios = require("axios");
        
        //Retrieve Salesforce Contact, Salesforce Account, and Tenant Request object information if missing and found via API call.
        //This is added to the user's object within the NetskopeID table.
        async function federated_sf_updater(nsidUserId) {

            async function getSfToken() {
                const options = {
                    method: 'POST',
                    url: event.secrets.SF_TURL,
                    headers: { "content-type": "application/x-www-form-urlencoded" },
                    data: "grant_type=client_credentials&client_id="+event.secrets.SF_KEY+"&client_secret="+event.secrets.SF_PWD
                };
      
                const token = await axios(options)
                .then(response => {
                    if (response.status === 200) {
                        let toJson = response.data;
                        let token = "Bearer " + toJson.access_token.toString();
                        return token;
                    }
                })
                .catch(async error => {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return null;
                });
                return token;
            }

            let sf_objects = {
                sf_account: {},
                sf_contact: {},
                ns_tenants: []
            };

            const token = await getSfToken();

            if (token !== null) {
                let email = "";
                let eventEmail = await sanitizeEmail(event.user.email??"");
                if (eventEmail.email !== null && eventEmail.error ===  null) {
                    email = eventEmail.email;
                }
                else {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    email = "";
                }

                let options = {
                    method: 'GET',
                    url: event.secrets.SF_AURL+"/services/data/v61.0/query?q=SELECT Id, IsDeleted, AccountId, LastName, FirstName, Name, Email, Title, CreatedDate FROM Contact WHERE Email='"+encodeURIComponent(email)+"' LIMIT 1",
                    headers: {"Content-Type": "application/json", "Authorization": token}
                };

                let lookupFailed = false;

                sf_objects.sf_contact = await axios(options)
                .then(response => {
                    let contact = {};
                    if (response.data.totalSize >= 1) {
                        let record = response.data.records[0];
                        contact = {"Id": record.Id??"", "AccountId": record.AccountId??"", "Name": record.Name??"", "FirstName": record.FirstName??"" , "LastName": record.LastName??"" , "Email": record.Email??"", "Title": record.Title??"", "IsDeleted": record.IsDeleted??"", "CreatedDate": record.CreatedDate??""};
                    }
                    else {
                        contact = {};
                    }
                    return contact;
                })
                .catch(async error => {
                    let errorCode = await error_code_generator(new Error(), "1061");
                    console.error("Backend Error. Error ID: " + errorCode);
                    lookupFailed = true;
                    let contact = {};
                    return contact;
                });

                if (sf_objects.sf_contact.hasOwnProperty('AccountId') && sf_objects.sf_contact.AccountId != "" && (await validate_sf_data(sf_objects.sf_contact.AccountId)) === true) {
                    let options = {
                        method: 'GET',
                        url: event.secrets.SF_AURL+"/services/data/v61.0/query?q=SELECT Id, IsDeleted, Name, Type, ParentId, OwnerId, Account_Status__c, Customer_Status__c, Primary_Partner_Type__c, Secondary_Partner_Type__c, Tertiary_Partner_Type__c FROM Account WHERE Id='"+sf_objects.sf_contact.AccountId+"' LIMIT 1",
                        headers: {"Content-Type": "application/json", "Authorization": token}
                    };
                
                    sf_objects.sf_account = await axios(options)
                    .then( response => {
                        let account = {};
                        if (response.data.totalSize >= 1) {
                            let record = response.data.records[0];
                            account = {"Id": record.Id??"", "IsDeleted":record.IsDeleted??"", "Name": record.Name??"", "Type": record.Type??"", "ParentId": record.ParentId??"", "OwnerId": record.OwnerId??"", "Account_Status__c": record.Account_Status__c??"", "Customer_Status__c": record.Customer_Status__c??"", "Primary_Partner_Type__c": record.Primary_Partner_Type__c??"", "Secondary_Partner_Type__c": record.Secondary_Partner_Type__c??"", "Tertiary_Partner_Type__c": record.Tertiary_Partner_Type__c??""};
                        }
                        else {
                            account = {};
                        }
                        return account;
                    })
                    .catch(async error => {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                        lookupFailed = true;
                        let account = {};
                        return account;
                    });

                    options = {
                        method: 'GET',
                        url: event.secrets.SF_AURL+"/services/data/v61.0/query?q=SELECT Name, Account_Id__c, Tenant_Type_Formula__c, Deprovisioning_done__c, Tenant_Provision_Status__c FROM Tenant_Request__c WHERE Account__c='"+sf_objects.sf_contact.AccountId+"'",
                        headers: {"Content-Type": "application/json", "Authorization": token}
                    };

                    sf_objects.ns_tenants = await axios(options)
                    .then( response => {
                        let tenants = [];
                        if (response.data.totalSize >= 1) {
                            let records = response.data.records;
                            for (let index = 0; index < records.length; index++) {
                                tenants.push({"Tenant Ticket": records[index].Name??"","Account_Id__c": records[index].Account_Id__c??"", "Tenant_Type_Formula__c": records[index].Tenant_Type_Formula__c??"", "Deprovisioning_done__c": records[index].Deprovisioning_done__c??"", "Tenant_Provision_Status__c": records[index].Tenant_Provision_Status__c??""});
                            }
                        }
                        else {
                            tenants = [];
                        }
                        return tenants;
                    })
                    .catch(async error => {
                        if (error.hasOwnProperty('response') && error.response.hasOwnProperty('data')) {
                            let errorCode = await error_code_generator(new Error(), "1061");
                            console.error("Backend Error. Error ID: " + errorCode);
                        }
                        else {
                            let errorCode = await error_code_generator(new Error(), "1061");
                            console.error("Backend Error. Error ID: " + errorCode);
                        }
                        lookupFailed = true;
                        let tenants = [];
                        return tenants;
                    });
                }

                // A thrown query (as opposed to a clean zero-row result) means we
                // couldn't determine the user's Salesforce state. Leave the DB untouched
                // so a transient outage can't blank good data or wrongly downgrade access.
                // A successful empty result still falls through and is persisted, so a
                // genuine contact/account deletion correctly reverts to default access.
                if (lookupFailed) {
                    return { ok: false, sf_objects: null };
                }

                if (nsidUserId) {
                    let UPDATED = await update_netskopeid_user(nsidUserId, sf_objects);
                    if (UPDATED !== true) {
                        let errorCode = await error_code_generator(new Error(), "1061");
                        console.error("Backend Error. Error ID: " + errorCode);
                        return { ok: false, sf_objects: null };
                    }
                }
                return { ok: true, sf_objects: sf_objects };
            }
            else {
                //Could not retrieve Salesforce token — unknown state, do not touch the DB.
                return { ok: false, sf_objects: null };
            }
        }

        //This function will create users within the NetskopeID table.
        async function create_netskope_id_user(user) {
            const { DynamoDBClient, PutItemCommand } = require("@aws-sdk/client-dynamodb");
            const { STSClient, AssumeRoleCommand } = require("@aws-sdk/client-sts");

            var created = null;
      	
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
                    const errorCode = await error_code_generator(new Error(),"1061");
                    created = new Error("Backend error. Error ID: " + errorCode);
                    return created;
                }
            } 
            catch (error) {
                const errorCode = await error_code_generator(new Error(),"1061");
                created = new Error("Backend error. Error ID: " + errorCode);
                return created;
            }

            const client = new DynamoDBClient({
                region: event.secrets.REG,
                credentials: {
                    accessKeyId: stsResponse.Credentials.AccessKeyId,
                    secretAccessKey: stsResponse.Credentials.SecretAccessKey,
                    sessionToken: stsResponse.Credentials.SessionToken
                }
            });
        
            const command = new PutItemCommand({
                TableName: event.secrets.TN,
                Item: marshall(user),
                ReturnConsumedCapacity: "TOTAL"
            });

            try {
        	    const response = await client.send(command);
                if (response.$metadata.hasOwnProperty("httpStatusCode") && response.$metadata.httpStatusCode === 200) {
                    created = true;
                    return created;
                }
                else {
                    const errorCode = await error_code_generator(new Error(),"1061");
                    created = new Error("Sign-up failed. Error ID: " + errorCode);
                    return created;
                }
	        }
	        catch (error) {
                const errorCode = await error_code_generator(new Error(),"1061");
        	    created = new Error("Backend error. Error ID: " + errorCode);
                return created;
	        }
        }

        if (event.connection.name !== "NetskopeID") {
            let USER = {};

            if (Object.prototype.hasOwnProperty.call(event.user.app_metadata, "nsid_user_id")) {
                USER = await get_netskopeid_user(event.user.app_metadata.nsid_user_id);
                if (USER.user !== null) {
                    USER = USER.user;

                    // entitlements/permissions are admin-managed; the DB is
                    // authoritative, so project them to session every login.
                    api.user.setAppMetadata('permissions',  USER.permissions  ?? []);
                    api.user.setAppMetadata('entitlements', USER.entitlements ?? []);
                    // roles/birthright are owned by Action 6 (group-based) for the
                    // group-based connection; projecting the DB copy would clobber it and
                    // the change would never persist. Only project for SF-eligible
                    // connections, where set_birthright_access manages the DB copy.
                    if (event.connection.name !== "NSKP-Preview") {
                        api.user.setAppMetadata('roles',      USER.roles      ?? []);
                        api.user.setAppMetadata('birthright', USER.birthright ?? []);
                    }

                    // IdP is authoritative for profile fields. Guard each so a
                    // transient missing value from the IdP doesn't blank the DB.
                    let profileUpdate = {};
                    if (event.user.email)       profileUpdate.email       = event.user.email;
                    if (event.user.given_name)  profileUpdate.given_name  = event.user.given_name;
                    if (event.user.family_name) profileUpdate.family_name = event.user.family_name;
                    if (event.user.name)        profileUpdate.name        = event.user.name;
                    if (event.user.nickname)    profileUpdate.nickname    = event.user.nickname;
                    if (typeof event.user.email_verified === "boolean") {
                        profileUpdate.email_verified = event.user.email_verified;
                    }
                    if (typeof event.user.blocked === "boolean") {
                        profileUpdate.blocked = event.user.blocked;
                    }
                    if (Object.prototype.hasOwnProperty.call(event.user.app_metadata, "federated")) {
                        profileUpdate.federated = event.user.app_metadata.federated;
                    }
					else {
						profileUpdate.federated = true;
					}

                    if (Object.keys(profileUpdate).length > 0) {
                        let UPDATED = await update_netskopeid_user(event.user.app_metadata.nsid_user_id, profileUpdate);
                        if (UPDATED !== true) {
                            let errorCode = await error_code_generator(new Error(), "1061-upd");
                            console.error("Backend Error. Error ID: " + errorCode);
                            return;
                        }
                    }

                    // Enrich with Salesforce data (sf_contact/sf_account/ns_tenants).
                    // federated_sf_updater hits Salesforce (token + up to 3 queries), so
                    // throttle it: refresh when no account is on record yet, or hourly.
                    const sfMissing = !USER.hasOwnProperty("sf_account") || Object.keys(USER.sf_account ?? {}).length === 0;
                    const sfStale = (dtu - (event.user.app_metadata.last_fed_sf_sync ?? 0)) >= 3600;
                    if (sfMissing || sfStale || event.user.app_metadata.last_fed_sf_sync === "") {
                        const SF = await federated_sf_updater(event.user.app_metadata.nsid_user_id);
                        // Only advance the throttle and apply fresh data on a conclusive
                        // lookup; a Salesforce outage leaves the DB untouched and retries
                        // on the next login rather than blanking/downgrading the user.
                        if (SF.ok) {
                            api.user.setAppMetadata("last_fed_sf_sync", dtu);
                            USER.sf_contact = SF.sf_objects.sf_contact;
                            USER.sf_account = SF.sf_objects.sf_account;
                            USER.ns_tenants = SF.sf_objects.ns_tenants;
                        }
                    }

                    // Compute Salesforce-based birthright/roles for federated users,
                    // mirroring the NetskopeID flow. No-ops for the group-based connection
                    // or when no sf_account is on record. On a failed lookup this runs
                    // against the existing cached sf_account, so access is not downgraded.
                    await set_birthright_access(USER);
                }
                else {
                    let errorCode = await error_code_generator(new Error(), "1061-get");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return;
                }
            }
            else {
                USER.email = event.user.email;
                USER.given_name = event.user.given_name??"";
                USER.family_name = event.user.family_name??"";
                USER.name = event.user.name??"";
                USER.nickname = event.user.nickname??(event.user.email ? event.user.email.split("@")[0] : "");
                USER.email_verified = event.user.email_verified??false;
                USER.created_at = Math.floor(Date.now() / 1000);
                USER.blocked = false;
                USER.permissions = event.user.app_metadata.permissions??[];
                USER.entitlements = event.user.app_metadata.entitlements??[];
                USER.roles = event.user.app_metadata.roles??[];
                USER.birthright = event.user.app_metadata.birthright??[];
                USER.fed_og_user_id = event.user.user_id;
                USER.user_id = uuidv4();
                let CREATE = await create_netskope_id_user(USER);
                if (CREATE === true) {
                    api.user.setAppMetadata('nsid_user_id', USER.user_id);
                    // Project entitlements/permissions to session on first login too;
                    // otherwise downstream actions (e.g. Gatekeeper) read undefined.
                    api.user.setAppMetadata('permissions',  USER.permissions  ?? []);
                    api.user.setAppMetadata('entitlements', USER.entitlements ?? []);
                    // Enrich the just-created record. Pass the new user_id directly:
                    // setAppMetadata above does not mutate event.user.app_metadata in
                    // this execution, so the helper can't read it from there yet.
                    const SF = await federated_sf_updater(USER.user_id);
                    // Only compute birthright on a conclusive lookup; if Salesforce was
                    // unreachable, leave the throttle unset so the next login retries.
                    if (SF.ok) {
                        api.user.setAppMetadata("last_fed_sf_sync", dtu);
                        USER.sf_contact = SF.sf_objects.sf_contact;
                        USER.sf_account = SF.sf_objects.sf_account;
                        USER.ns_tenants = SF.sf_objects.ns_tenants;
                        await set_birthright_access(USER);
                    }
                    else {
                        // Salesforce was unreachable on this first login, so
                        // set_birthright_access never ran and birthright would be
                        // undefined. Grant the most basic default access so
                        // downstream actions (Gatekeeper) have a value; the next
                        // login retries the lookup and computes real birthright.
                        api.user.setAppMetadata('birthright', ['Dashboard']);
                    }
                }
                else {
                    let errorCode = await error_code_generator(new Error(), "1061-new");
                    let detail = (CREATE instanceof Error && CREATE.message) ? " — " + CREATE.message : "";
                    console.error("Backend Error. Error ID: " + errorCode + detail);
                    return;
                }
            }
        }
    }

    //Updates to users wtihin the NetskopeID table that need to be pushed on each login event.
    //We do this to make sure we capture changes to the entitlements and permissions fields.
    async function sync_each_login() {
        if (event.connection.name === "NetskopeID") {
            var SYNC_EVERYTIME = {
                entitlements: event.user.app_metadata.entitlements,
                permissions: event.user.app_metadata.permissions,
            };

            var UPDATED = await update_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id, SYNC_EVERYTIME);

            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }
            return;
        }
    }

    const dtn = Date.now();
    const dtu = (dtn-(dtn%1000))/1000;

    //Run Every Login
    await create_impartner_user();

    await update_auth0id_within_impartner();

    await community_provisioning();
    
    await check_community_user_approval_status();

    await sync_federated_user_to_netskopeid();

    await sync_each_login();

    //Run Daily Sync functions
    if (event.connection.name === "NetskopeID" && ((dtu - (event.user.app_metadata.last_daily_sync??dtu-86401)) >= 86400 || event.user.app_metadata.last_daily_sync === "")) {
        var USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

        if (USER.user !== null) {
            USER = USER.user;
            //console.log("Daily Sync...");
            var DAILY_UPDATES = {
                last_daily_sync: dtu
            };
            var UPDATED = await update_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id, DAILY_UPDATES);
            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1061");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            api.user.setAppMetadata("last_daily_sync", dtu);
        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1061");
            console.error("Backend Error. Error ID: " + errorCode);
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1061");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    //Run Hourly Sync functions
    if (event.connection.name === "NetskopeID" && ((dtu - (event.user.app_metadata.last_sync??dtu-3601)) >= 3600 || event.user.app_metadata.last_sync === "")) {
        var USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

        if (USER.user !== null) {
            USER = USER.user;
            //console.log("Hourly Sync...");

            await set_birthright_access(USER);

        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1061");
            console.error("Backend Error. Error ID: " + errorCode);
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1061");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }
    return;
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
