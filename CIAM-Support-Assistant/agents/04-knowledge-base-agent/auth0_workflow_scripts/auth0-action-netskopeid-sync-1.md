# Auth0 Action: NetskopeID-Sync-1

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### NetskopeID-Sync-1

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 548246b5-264d-4b2f-a91d-2d766cee1933

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
    //Bypass any login events from the migration script.
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

    const axios = require('axios');
    const { marshall,unmarshall } = require("@aws-sdk/util-dynamodb");
    const { v4: uuidv4 } = require('uuid');

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
                let errorCode = await error_code_generator(new Error(), "1051");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1051");
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
                let errorCode = await error_code_generator(new Error(), "1051");
                USER.error = "Backend Error. Error ID: " + errorCode;
                return USER;
            }   
        }
        catch (error) {
            USER.user = null;
            let errorCode = await error_code_generator(new Error(), "1051");
            USER.error = "Backend Error: Error ID: " + errorCode;
            return USER;
        }
    }

    //Update a user object in the NetskopeID table.
    async function update_netskopeid_user(id, user) {
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
                let errorCode = await error_code_generator(new Error(), "1051");
                UPDATED = "Backend Error. Error ID: " + errorCode;
                return UPDATED;
            }
        }
        catch (error) {
            let errorCode = await error_code_generator(new Error(), "1051");
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
            let errorCode = await error_code_generator(new Error(), "1051");
            UPDATED = "Backend Error. Error ID: " + errorCode;
            return UPDATED;
        }
    }

    //Add missing fields for a user.
    async function add_missing_fields() {
        if (event.connection.name === "NetskopeID") {
            let USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);
          
            if (USER.user !== null) {
                USER = USER.user;
                let count = 0;
                let update_object =  {};
            
                //Add roles array if missing.
                if (!USER.hasOwnProperty("roles")) {
                    update_object.roles = [];
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("roles")) {
                    api.user.setAppMetadata("roles", []);
                }


                //Add entitlements array if missing.
                if (!USER.hasOwnProperty("entitlements")) {
                    update_object.entitlements = [];
                    api.user.setAppMetadata("entitlements", []);
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("entitlements")) {
                    api.user.setAppMetadata("entitlements", []);
                }

                //Add birthright array if missing.
                if (!USER.hasOwnProperty("birthright")) {
                    update_object.birthright = [];
                    api.user.setAppMetadata("birthright", []);
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("birthright")) {
                    api.user.setAppMetadata("birthright", []);
                } 

                //Add permissions array if missing.
                if (!USER.hasOwnProperty("permissions")) {
                    update_object.permissions = [];
                    api.user.setAppMetadata("permissions", []);
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("permissions")) {
                    api.user.setAppMetadata("permissions", []);
                }

                //Add Send ID to user object.
                if (!USER.hasOwnProperty("send_id")) {
                    update_object.send_id = true;
                    count++;
                }

                //Add last_sync to user object if missing
                if (!USER.hasOwnProperty("last_sync")) {
                    update_object.last_sync = "";
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("last_sync")) {
                    api.user.setAppMetadata("last_sync", "");
                }

                //Add last_daily_sync to user object if missing
                if (!USER.hasOwnProperty("last_daily_sync")) {
                    api.user.setAppMetadata("last_daily_sync", "");
                    update_object.last_daily_sync = "";
                    count++;
                }
                if (!event.user.app_metadata.hasOwnProperty("last_daily_sync")) {
                    api.user.setAppMetadata("last_daily_sync", "");
                }

                if (count >= 1) {
                    let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), update_object);
                    if (UPDATED !== true) {
                        let errorCode = await error_code_generator(new Error(), "1051");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                    else {
                        return;
                    }
                }
                else {
                    return;
                }
            }
            else if (USER.error !== null) {
                let errorCode = await error_code_generator(new Error(), "1051");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            else {
                let errorCode = await error_code_generator(new Error(), "1051");
                console.error("Backend Error. Error ID: " + errorCode);
            }
        }
        else {
            return;
        }
    }

    //Add missing fields for federated users.
    async function set_federated_user_metadata() {
        try {
            if (event.connection.name!="NetskopeID"){
                try {
                    if (event.connection.name === "NSKP-Preview") {
                        //Set metadata for regular partner portal users.
                        /*
                        if (event.user.groups?.includes("prod-cust-nsid-partnerportal-user-grn") && event.stats.logins_count<=2) {
                            api.user.setAppMetadata("federated", true);
                            api.user.setAppMetadata("send_id", true);
                            api.user.setAppMetadata("entitlements", []);
                            api.user.setAppMetadata("roles", ["nskp-internal","nskp-partner"]);
                            api.user.setAppMetadata("birthright", ["Partner","Academy","Notification","Dashboard"]);
                        }
                        */
                        if (event.user.groups?.includes("prod-cust-nsid-partnerportal-user-grn")) {
                            if (!event.user.app_metadata.hasOwnProperty("federated")) {
                                api.user.setAppMetadata("federated", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("send_id")) {
                                api.user.setAppMetadata("send_id", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("entitlements")) {
                                api.user.setAppMetadata("entitlements", []);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("roles")) {
                                api.user.setAppMetadata("roles", ["nskp-internal","nskp-partner"]);
                            }
                            if (event.user.app_metadata.hasOwnProperty("roles") && (!event.user.app_metadata.roles.includes("nskp-internal") || !event.user.app_metadata.roles.includes("nskp-partner"))) {
                                let current_roles = event.user.app_metadata.roles;
                                current_roles.push("nskp-partner");
                                current_roles.push("nskp-internal");
                                let new_roles = [...new Set(current_roles)];
                                api.user.setAppMetadata("roles", new_roles);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("birthright")) {
                                api.user.setAppMetadata("birthright", ["Partner","Academy","Notification","Dashboard"]);
                            }
                            if (event.user.app_metadata.hasOwnProperty("birthright") && (!event.user.app_metadata.birthright.includes("Partner") || !event.user.app_metadata.birthright.includes("Academy") || !event.user.app_metadata.birthright.includes("Notification") || !event.user.app_metadata.birthright.includes("Dashboard"))) {
                                let current_birthright = event.user.app_metadata.birthright;
                                current_birthright.push("Partner");
                                current_birthright.push("Academy");
                                current_birthright.push("Notification");
                                current_birthright.push("Dashboard");
                                let new_birthright = [...new Set(current_birthright)];
                                api.user.setAppMetadata("birthright", new_birthright);
                            }
                            if (event.user.app_metadata.hasOwnProperty("birthright") && !event.user.groups?.includes("prod-cust-nsid-partnerportal-prime-user-grn") && event.user.app_metadata.birthright.includes("Prime")) {
                                let current_birthright = event.user.app_metadata.birthright.filter(b => b !== "Prime");
                                let new_birthright = [...new Set(current_birthright)];
                                api.user.setAppMetadata("birthright", new_birthright);
                            }
                            if (event.user.app_metadata.hasOwnProperty("birthright") && !event.user.groups?.includes("prod-cust-nsid-supportportal-user-grn") && event.user.app_metadata.birthright.includes("Support")) {
                                let current_birthright = event.user.app_metadata.birthright.filter(b => b !== "Support");
                                let new_birthright = [...new Set(current_birthright)];
                                api.user.setAppMetadata("birthright", new_birthright);
                            }
                        }
                        //Set metadata for prime partner portal users.
                        /*
                        if (event.user.groups?.includes("prod-cust-nsid-partnerportal-prime-user-grn") && event.stats.logins_count<=2) {
                            api.user.setAppMetadata("federated", true);
                            api.user.setAppMetadata("send_id", true);
                            api.user.setAppMetadata("entitlements", []);
                            api.user.setAppMetadata("roles", ["nskp-internal","nskp-partner","nskp-prime"]);
                            api.user.setAppMetadata("birthright", ["Prime","Partner","Academy","Notification","Dashboard"]);
                        }
                        */
                        if (event.user.groups?.includes("prod-cust-nsid-partnerportal-prime-user-grn")) {
                            if (!event.user.app_metadata.hasOwnProperty("federated")) {
                                api.user.setAppMetadata("federated", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("send_id")) {
                                api.user.setAppMetadata("send_id", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("entitlements")) {
                                api.user.setAppMetadata("entitlements", []);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("roles")) {
                                api.user.setAppMetadata("roles", ["nskp-internal","nskp-partner","nskp-prime"]);
                            }
                            if (event.user.app_metadata.hasOwnProperty("roles") && (!event.user.app_metadata.roles.includes("nskp-internal") || !event.user.app_metadata.roles.includes("nskp-partner") || !event.user.app_metadata.roles.includes("nskp-prime"))) {
                                let current_roles = event.user.app_metadata.roles;
                                current_roles.push("nskp-partner");
                                current_roles.push("nskp-internal");
                                current_roles.push("nskp-prime");
                                let new_roles = [...new Set(current_roles)];
                                api.user.setAppMetadata("roles", new_roles);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("birthright")) {
                                api.user.setAppMetadata("birthright", ["Prime","Partner","Academy","Notification","Dashboard"]);
                            }
                            if (event.user.app_metadata.hasOwnProperty("birthright") && (!event.user.app_metadata.birthright.includes("Prime") || !event.user.app_metadata.birthright.includes("Partner") || !event.user.app_metadata.birthright.includes("Academy") || !event.user.app_metadata.birthright.includes("Notification") || !event.user.app_metadata.birthright.includes("Dashboard"))) {
                                let current_birthright = event.user.app_metadata.birthright;
                                current_birthright.push("Prime");
                                current_birthright.push("Partner");
                                current_birthright.push("Academy");
                                current_birthright.push("Notification");
                                current_birthright.push("Dashboard");
                                let new_birthright = [...new Set(current_birthright)];
                                api.user.setAppMetadata("birthright", new_birthright);
                            }
                            if (event.user.app_metadata.hasOwnProperty("birthright") && !event.user.groups?.includes("prod-cust-nsid-supportportal-user-grn") && event.user.app_metadata.birthright.includes("Support")) {
                                let current_birthright = event.user.app_metadata.birthright.filter(b => b !== "Support");
                                let new_birthright = [...new Set(current_birthright)];
                                api.user.setAppMetadata("birthright", new_birthright);
                            }
                        }
                        //Set metadata for regular support portal users.
                        /*
                        if (event.user.groups?.includes("prod-cust-nsid-supportportal-user-grn") && event.stats.logins_count<=2) {
                            api.user.setAppMetadata("federated", true);
                            api.user.setAppMetadata("send_id", true);
                            api.user.setAppMetadata("entitlements", []);
                            api.user.setAppMetadata("roles", ["nskp-internal"]);
                            api.user.setAppMetadata("birthright", ["Support","Academy","Notification","Dashboard"]);
                        }
                        */
                        if (event.user.groups?.includes("prod-cust-nsid-supportportal-user-grn")) {
                            const hasPartnerPortalUser = event.user.groups?.includes("prod-cust-nsid-partnerportal-user-grn");
                            const hasPartnerPortalPrimeUser = event.user.groups?.includes("prod-cust-nsid-partnerportal-prime-user-grn");

                            if (!event.user.app_metadata.hasOwnProperty("federated")) {
                                api.user.setAppMetadata("federated", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("send_id")) {
                                api.user.setAppMetadata("send_id", true);
                            }
                            if (!event.user.app_metadata.hasOwnProperty("entitlements")) {
                                api.user.setAppMetadata("entitlements", []);
                            }
                            const current_roles = Array.isArray(event.user.app_metadata.roles) ? [...event.user.app_metadata.roles] : [];
                            const preserved_roles = current_roles.filter(r => r !== "nskp-internal" && r !== "nskp-partner" && r !== "nskp-prime");
                            const roles = [
                                ...preserved_roles,
                                "nskp-internal"
                            ];
                            if (hasPartnerPortalUser || hasPartnerPortalPrimeUser) {
                                roles.push("nskp-partner");
                            }
                            if (hasPartnerPortalPrimeUser) {
                                roles.push("nskp-prime");
                            }
                            api.user.setAppMetadata("roles", [...new Set(roles)]);
                            const current_birthright = Array.isArray(event.user.app_metadata.birthright) ? [...event.user.app_metadata.birthright] : [];
                            const preserved_birthright = current_birthright.filter(b => b !== "Partner" && b !== "Prime");
                            const birthright = [
                                ...preserved_birthright,
                                "Support",
                                "Academy",
                                "Notification",
                                "Dashboard"
                            ];
                            if (hasPartnerPortalUser || hasPartnerPortalPrimeUser) {
                                birthright.push("Partner");
                            }
                            if (hasPartnerPortalPrimeUser) {
                                birthright.push("Prime");
                            }
                            api.user.setAppMetadata("birthright", [...new Set(birthright)]);
                        }
                    }
                    else if (event.connection.name !== "NSKP-Preview" && event.user.groups?.includes("ns-partner-user") && event.stats.logins_count<=2) {
                        api.user.setAppMetadata("federated", true);
                        api.user.setAppMetadata("send_id", true);
                    }
                    else {
                        api.user.setAppMetadata("federated", true);
                    }
                }
                catch(err) {
                    let errorCode = await error_code_generator(new Error(), "1071");
                    console.error("Backend Error. Error ID: " + errorCode);
                }
            }
        }
        catch(err){
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    //Retrieve Salesforce Contact, Salesforce Account, and Tenant Request object information if missing and found via API call.
    //This is added to the user's object within the NetskopeID table.
    async function sf_updater() {

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
                let errorCode = await error_code_generator(new Error(), "1051");
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
                let errorCode = await error_code_generator(new Error(), "1051");
                console.error("Backend Error. Error ID: " + errorCode);
                email = "";
            }

            let options = {
                method: 'GET',
                url: event.secrets.SF_AURL+"/services/data/v61.0/query?q=SELECT Id, IsDeleted, AccountId, LastName, FirstName, Name, Email, Title, CreatedDate FROM Contact WHERE Email='"+encodeURIComponent(email)+"' LIMIT 1",
                headers: {"Content-Type": "application/json", "Authorization": token}
            };

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
                let errorCode = await error_code_generator(new Error(), "1051");
                console.error("Backend Error. Error ID: " + errorCode);
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
                    let errorCode = await error_code_generator(new Error(), "1051");
                    console.error("Backend Error. Error ID: " + errorCode);
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
                        let errorCode = await error_code_generator(new Error(), "1051");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                    else {
                        let errorCode = await error_code_generator(new Error(), "1051");
                        console.error("Backend Error. Error ID: " + errorCode);
                    }
                    let tenants = [];
                    return tenants;
                });

                let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), sf_objects);
                if (UPDATED !== true) {
                    let errorCode = await error_code_generator(new Error(), "1051");
                    console.error("Backend Error. Error ID: " + errorCode);
                }
                return;
            }
            else {
                //Missing salesforce contact information.
                let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), sf_objects);
                if (UPDATED !== true) {
                    let errorCode = await error_code_generator(new Error(), "1051");
                    console.error("Backend Error. Error ID: " + errorCode);
                }
                return;
            }
        }
        else {
            //Could not retrieve Salesforce token.
            let UPDATED = await update_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id), sf_objects);
            if (UPDATED !== true) {
                let errorCode = await error_code_generator(new Error(), "1051");
                console.error("Backend Error. Error ID: " + errorCode);
            }
            return;
        }
    }


    const dtn = Date.now();
    const dtu = (dtn-(dtn%1000))/1000;

    //Run Every Login

    await add_missing_fields();

    await set_federated_user_metadata();
      
    //Run Daily Sync functions
    if (event.connection.name === "NetskopeID" && ((dtu - (event.user.app_metadata.last_daily_sync??dtu-86401)) >= 86400 || event.user.app_metadata.last_daily_sync === "" || !event.user.app_metadata.hasOwnProperty("last_daily_sync"))) {
        let USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);

        if (USER.user !== null) {
            USER = USER.user;
        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1051");
            console.error("Backend Error. Error ID: " + errorCode);
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1051");
            console.error("Backend Error. Error ID: " + errorCode);
        }
    }

    //Run Hourly Sync functions
    if (event.connection.name === "NetskopeID" && ((dtu - (event.user.app_metadata.last_sync??dtu-3601)) >= 3600 || event.user.app_metadata.last_sync === "" || !event.user.app_metadata.hasOwnProperty("last_sync"))) {
        let USER = await get_netskopeid_user((event.user.user_id.split("|")[1]??event.user.user_id));

        if (USER.user !== null) {
            USER = USER.user;

            //Retrieve Salesforce Contact, Account, and Tenant Request information.
            await sf_updater();
        }
        else if (USER.error !== null) {
            let errorCode = await error_code_generator(new Error(), "1051");
            console.error("Backend Error. Error ID: " + errorCode);
        }
        else {
            let errorCode = await error_code_generator(new Error(), "1051");
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
