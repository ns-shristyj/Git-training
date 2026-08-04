# Auth0 Action: RBAC - Consolidated

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### RBAC - Consolidated

- **Trigger(s):** post-login
- **Status:** built
- **Action ID:** 8bc8603f-7b71-434e-907b-7a0d94d97773

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
    //Bypass for migration script
    if (event.client.client_id === event.secrets.b_id) {
        return;
    }

    // Shared mutable state for array-valued app_metadata fields that multiple
    // helpers below all want to modify. Each helper mutates *_state.current in
    // place; a single setAppMetadata call at the bottom of this handler commits
    // the final value. This eliminates the last-write-wins race that occurs when
    // multiple helpers independently call setAppMetadata for the same key, since
    // event.user.app_metadata is a start-of-action snapshot that doesn't reflect
    // prior setAppMetadata calls in the same execution.
    // Helpers must NOT call setAppMetadata("entitlements", ...) or
    // setAppMetadata("permissions", ...) directly; mutate the shared state instead.
    // sync_each_login reads from these to push the latest values to DynamoDB.
    const initial_entitlements = Array.isArray(event.user.app_metadata?.entitlements)
        ? [...event.user.app_metadata.entitlements]
        : [];
    const entitlement_state = {
        initial: initial_entitlements,
        current: [...initial_entitlements]
    };

    const initial_permissions = Array.isArray(event.user.app_metadata?.permissions)
        ? [...event.user.app_metadata.permissions]
        : [];
    const permissions_state = {
        initial: initial_permissions,
        current: [...initial_permissions]
    };

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

    // Update a user object in the NetskopeID table.
    // Currently unused in this action — kept here in case future helpers need it.
    async function update_netskopeid_user(id, user) {
        const { marshall,unmarshall } = require("@aws-sdk/util-dynamodb");
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

    //Set SAML accountId attribute for federated Partner Portal users
    async function set_federated_partner_portal_attributes() {
        try {
            if(event.client.client_id === event.secrets.imp_cid && event.user?.partner_id && event.connection.name != "NetskopeID") {
                api.samlResponse.setAttribute("accountId",event.user.partner_id);
                return;
            }
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Check if user is active in Impartner before allowing access to Partner Portal, and set Block-Partner entitlement accordingly.
    async function get_partner_portal_user() {
        const axios = require("axios");
        async function get_user() {
            // Backslash-escape \ and ' before embedding the email into Impartner's
            // filter expression. URL encoding (handled by axios via params) protects
            // transport but not the filter language itself — a raw single quote in
            // the email would terminate the literal early or enable injection.
            const safeEmail = (event.user.email || "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
            let partner_user = await axios({
				method: "get",
				headers: {"Content-Type": "application/json"},
				url: "https://stage.impartner.live/api/objects/v1/User",
				params: {filter: "email='" + safeEmail + "'", fields: "email,id,isActive,account"},
				auth: {username: event.secrets.impEmail, password: event.secrets.impPwd}
			})
			.then(async function(response) {
				let partner_user = null;
                try {
					let userCount = response.data.data.results.length;
					if (userCount >= 1) {
                        partner_user = response.data.data.results[0];
						if (partner_user.hasOwnProperty("isActive") ) {
                            return partner_user;
						}
						else {
							console.log("No isActive field found for the user. Skipping.");
                            partner_user = null;
                            return partner_user;
						}
					}
					else {
						console.log("No matching user found. Skipping.");
                        return partner_user;
					}
				}
				catch (error){
					let errorCode = await error_code_generator(new Error(), "1071");
					console.error("Backend Error. Error ID: " + errorCode);
                    return partner_user;
				}
			})
			.catch(async function(error){
                let partner_user = null;
				let errorCode = await error_code_generator(new Error(), "1071");
				console.error("Backend Error. Error ID: " + errorCode);
                return partner_user;
			})
            return partner_user;
        }

        // Look up the user's associated Impartner Account so we can block users
        // whose individual record is still active but whose Account has been
        // deactivated. Returns the account object or null on miss/error.
        async function get_account(accountId) {
            let account = await axios({
                method: "get",
                headers: {"Content-Type": "application/json"},
                url: "https://stage.impartner.live/api/objects/v1/Account",
                params: {filter: "id='" + accountId + "'", fields: "id,isActive"},
                auth: {username: event.secrets.impEmail, password: event.secrets.impPwd}
            })
            .then(async function(response) {
                let account = null;
                try {
                    let accountCount = response.data.data.results.length;
                    if (accountCount >= 1) {
                        account = response.data.data.results[0];
                        if (account.hasOwnProperty("isActive")) {
                            return account;
                        }
                        else {
                            console.log("No isActive field found for the account. Skipping.");
                            account = null;
                            return account;
                        }
                    }
                    else {
                        console.log("No matching account found. Skipping.");
                        return account;
                    }
                }
                catch (error) {
                    let errorCode = await error_code_generator(new Error(), "1071");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return account;
                }
            })
            .catch(async function(error) {
                let account = null;
                let errorCode = await error_code_generator(new Error(), "1071");
                console.error("Backend Error. Error ID: " + errorCode);
                return account;
            });
            return account;
        }

        try {
            if ((event.user.app_metadata.birthright?.includes("Partner") || event.user.app_metadata.entitlements?.includes("Partner")) && (event.client.name.includes("Netskope Partner Portal") || event.client.name === "CIAM Dashboard")) {
                let partner_user = await get_user();
                if (partner_user) {
                    //console.log(partner_user);

                    // If the user is active, also verify their associated Account is active.
                    // Account inactive => block as if the user were inactive.
                    // Missing accountId => fail-closed (block). A Partner-tier user without an
                    //   associated Account is anomalous and should not be trusted with access.
                    // Account lookup fails (network) => preserve existing entitlement state.
                    let accountIsActive = true;
                    if (partner_user.isActive === true) {
                        if (!partner_user.accountId) {
                            accountIsActive = false;
                        }
                        else {
                            const account = await get_account(partner_user.accountId);
                            //console.log(account);
                            if (account === null) {
                                return;
                            }
                            accountIsActive = (account.isActive === true);
                        }
                    }

                    if (partner_user.isActive === true && accountIsActive) {
                        const idx = entitlement_state.current.indexOf("Block-Partner");
                        if (idx !== -1) entitlement_state.current.splice(idx, 1);
                    }
                    else {
                        if (!entitlement_state.current.includes("Block-Partner")) {
                            entitlement_state.current.push("Block-Partner");
                        }
                    }
                }
                else {
                    return;
                }
            }
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Set OIDC Claims for Community
    // customRoles per Community docs accepts a comma-separated list of role IDs
    // (e.g. "15,20"). Users with both Partner and Support birthrights receive both.
    async function set_netskope_community_attributes() {
        try {
            if (event.client.metadata.addCustomClaims !== "true") return;

            const md = event.user.app_metadata || {};
            const hasPartner = md.birthright?.includes("Partner") || md.entitlements?.includes("Partner");
            const hasSupport = md.birthright?.includes("Support") || md.entitlements?.includes("Support");

            const roles = [];
            if (hasPartner) roles.push("15");
            if (hasSupport) roles.push("20");

            if (roles.length > 0) {
                api.idToken.setCustomClaim("customRoles", roles.join(","));
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Check if user is banned in the community and set Block-Comm entitlement accordingly.
    async function get_netskope_community_user() {
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
            .catch(error => {
                console.log(JSON.stringify(error.response?.data ?? { message: error.message }));
                return null;
            });
            return token;
        }

        async function get_user(token) {
            let options = {
                method: "GET",
                url: event.secrets.C_URL + "/user/email/" + encodeURIComponent(event.user.email?event.user.email:""),
                headers: {"Content-Type": "application/json", "Authorization": token}
            }
            const community_user = await axios(options)
            .then(response => {
                if (response.status === 200) {
                    return response.data;
                }
            })
            .catch(error => {
                console.log(JSON.stringify(error.response?.data ?? { message: error.message }));
                return null;
            });
            return community_user;
        }

        try {
            const md = event.user.app_metadata || {};
            const hasCommunity = md.birthright?.includes("Community") || md.entitlements?.includes("Community");
            const isCommunityClient = event.client.name.includes("Netskope Community") || event.client.name === "CIAM Dashboard";

            if (event.connection.name !== "NetskopeID") return;
            if (!hasCommunity) return;
            if (!isCommunityClient) return;
            if (md.pending_community_user === true) return;
            if (md.pending_community_approval === true) return;

            const token = await get_community_token();
            if (!token) {
                let errorCode = await error_code_generator(new Error(), "1071");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }

            const community_user = await get_user(token);
            if (!community_user) {
                let errorCode = await error_code_generator(new Error(), "1071");
                console.error("Backend Error. Error ID: " + errorCode);
                return;
            }

            const banned = Array.isArray(community_user.roles)
                && community_user.roles.some(r => r?.auth_item?.name === "roles.banned");

            if (banned) {
                if (!entitlement_state.current.includes("Block-Comm")) {
                    entitlement_state.current.push("Block-Comm");
                }
            }
            else {
                const idx = entitlement_state.current.indexOf("Block-Comm");
                if (idx !== -1) entitlement_state.current.splice(idx, 1);
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Set Username as SAML Name ID for Support Portal logins.
    async function set_netskope_support_portal_attributes() {
        try {
            if (event.client.name.includes("Netskope Support")) {
                if (event.connection.name === "NetskopeID") {
                    api.samlResponse.setAttribute('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier', event.user.username??event.user.user_id);

                    api.samlResponse.setNameIdentifierProbes([
                        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier',
                        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
                    ]);
                }
                else if (event.connection.name === "NSKP-Preview") {
                    api.samlResponse.setAttribute('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier', event.user.email+".fullcopy");
                    api.samlResponse.setAttribute('Email', event.user.email+".invalid");

                    api.samlResponse.setNameIdentifierProbes([
                        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier',
                        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'
                    ]);
                }
            }
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Check if user is active in Salesforce before allowing access to Support Portal, and set Block-Supp entitlement accordingly.
    async function get_netskope_support_user() {
        const axios = require("axios");
        async function get_salesforce_token() {
            let token = await axios({
                method: "POST",
                url: event.secrets.SF_TURL,
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                data: "grant_type=client_credentials&client_id="+event.secrets.SF_KEY+"&client_secret="+event.secrets.SF_PWD
            }).then(response => {
                let token = null;
                if (response.status === 200) {
                    token = "Bearer " + response.data.access_token.toString();
                    return token;
                }
                else {
                    console.log(response.status)
                    return token;
                }
            })
            .catch(error => {
                let token = null;
                return token;
            });

            return token;
        }

        async function get_user(token) {
            // SOQL escape: backslash-escape \ and ' before string concatenation.
            // encodeURIComponent does not protect SOQL — Salesforce decodes the URL
            // before parsing, so a raw single quote in the email would break the query
            // or open an injection path. Let axios handle URL encoding via params.
            const safeEmail = (event.user.email || "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
            const soql = "SELECT Id, Alias, CompanyName, Email, FirstName, IsActive, IsPortalEnabled, LastName, Name, PortalRole, Username, UserType FROM User WHERE Email='" + safeEmail + "' LIMIT 5";

            // Result shape: { user, error }
            //   user:  the Salesforce record, or null if no match was found
            //   error: true if the API call failed (token expired, network, 5xx, etc.)
            // Distinguishing these lets the caller fail-closed on errors (leave
            // entitlements and pending flag untouched) while still treating
            // "no match" as a first-time registration case.
            const result = await axios({
                method: "GET",
                url: event.secrets.SF_AURL + "/services/data/v61.0/query",
                params: { q: soql },
                headers: { "Content-Type": "application/json", "Authorization": token }
            })
            .then(async response => {
                if (response.status === 200) {
                    if (response.data.totalSize > 0) {
                        // Salesforce can return multiple User records for the same Email.
                        // Treat the identity as active if AT LEAST ONE matching record is
                        // active: prefer an IsActive === true record, otherwise fall back
                        // to the first record so the inactive -> Block-Supp path still runs.
                        const records = response.data.records;
                        const active_user = records.find(r => r.IsActive === true);
                        return { user: active_user || records[0], error: false };
                    }
                    return { user: null, error: false };
                }
                const errorCode = await error_code_generator(new Error(),"0041");
                console.error("Backend Error. Error ID: " + errorCode);
                return { user: null, error: true };
            })
            .catch(async error => {
                const errorCode = await error_code_generator(new Error(),"0041");
                console.error("Backend Error. Error ID: " + errorCode);
                return { user: null, error: true };
            });
            return result;
        }

        try {
            if ((event.user.app_metadata.birthright?.includes("Support") || event.user.app_metadata.entitlements?.includes("Support")) && (event.client.name.includes("Netskope Support") || event.client.name === "CIAM Dashboard")) {
                let token = await get_salesforce_token();
                if (token) {
                    const { user: support_user, error: sf_error } = await get_user(token);
                    // Fail-closed on API errors: preserve existing Block-Supp / pending state.
                    // A transient Salesforce outage should not flip a previously-blocked user
                    // to allowed, nor should it tag a known-good user as pending registration.
                    if (sf_error) {
                        return;
                    }
                    if (support_user) {
                        if (event.user.app_metadata.hasOwnProperty("pending_support_user") && event.user.app_metadata.pending_support_user === true) {
                            api.user.setAppMetadata("pending_support_user", false);
                        }

                        if (support_user.IsActive === true) {
                            const idx = entitlement_state.current.indexOf("Block-Supp");
                            if (idx !== -1) entitlement_state.current.splice(idx, 1);
                        }
                        else {
                            if (!entitlement_state.current.includes("Block-Supp")) {
                                entitlement_state.current.push("Block-Supp");
                            }
                        }
                    }
                    // No matching user found in Salesforce (call succeeded, zero results).
                    // First-time login: mark pending so manual intervention can resolve registration.
                    else {
                        if (!event.user.app_metadata.hasOwnProperty("pending_support_user")) {
                            api.user.setAppMetadata("pending_support_user", true);
                            return;
                        }
                        else {
                            return;
                        }
                    }
                }
                else {
                    let errorCode = await error_code_generator(new Error(), "1071");
                    console.error("Backend Error. Error ID: " + errorCode);
                    return;
                }
            }
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Set attributes for Netskope Academy (SkillJar)
    async function set_netskope_academy_attributes() {
        try{
			if (event.client.name.includes("Netskope Academy")) {
				if (event.connection.name === "NetskopeID") {
					let USER = await get_netskopeid_user(event.user.user_id.split("|")[1]??event.user.user_id);
					if (USER.user !== null) {
						USER = USER.user;
						if (USER.hasOwnProperty('sf_account') && USER.sf_account.hasOwnProperty("Account_Status__c") && USER.sf_account.Account_Status__c !== null && USER.sf_account.Account_Status__c !== undefined && USER.sf_account.Account_Status__c !== "") {
							if (USER.sf_account.Account_Status__c.includes("Prospect") || USER.sf_account.Account_Status__c.includes("Customer")) {
								api.samlResponse.setAttribute("Client Account Name", USER.sf_account.Name);
								api.samlResponse.setAttribute("User Account Type", "Prospect/Customer");
								// If the user has valid given_name and family_name values within the database
								// AND the Auth0 shadow copy does not have a valid given_name and family_name values OR the Auth0 shadow copy values for given_name and family_name are blank.
								// Send the database values via SAML Attributes.
								if ((USER.hasOwnProperty("given_name") && USER.hasOwnProperty("family_name") && USER.given_name !== "" && USER.family_name !== "") && (!event.user.hasOwnProperty("given_name") || !event.user.hasOwnProperty("family_name") || (event.user.hasOwnProperty("given_name") && (event.user.given_name === "" || event.user.given_name === null || event.user.given_name === undefined)) || (event.user.hasOwnProperty("family_name") && (event.user.family_name === "" || event.user.family_name === null || event.user.family_name === undefined)))) {
									api.samlResponse.setAttribute("First Name", USER.given_name);
									api.samlResponse.setAttribute("Last Name", USER.family_name);
								}
							}
							else if  (USER.sf_account.Account_Status__c.includes("Partner")) {
								api.samlResponse.setAttribute("Client Account Name", USER.sf_account.Name);
								api.samlResponse.setAttribute("User Account Type", "Partner");
								// If the user has valid given_name and family_name values within the database
								// AND the Auth0 shadow copy does not have a valid given_name and family_name values OR the Auth0 shadow copy values for given_name and family_name are blank.
								// Send the database values via SAML Attributes.
								if ((USER.hasOwnProperty("given_name") && USER.hasOwnProperty("family_name") && USER.given_name !== "" && USER.family_name !== "") && (!event.user.hasOwnProperty("given_name") || !event.user.hasOwnProperty("family_name") || (event.user.hasOwnProperty("given_name") && (event.user.given_name === "" || event.user.given_name === null || event.user.given_name === undefined)) || (event.user.hasOwnProperty("family_name") && (event.user.family_name === "" || event.user.family_name === null || event.user.family_name === undefined)))) {
									api.samlResponse.setAttribute("First Name", USER.given_name);
									api.samlResponse.setAttribute("Last Name", USER.family_name);
								}
							}
							else {
								let errorCode = await error_code_generator(new Error(), "1071");
								api.session.revoke("Backend Error. Error ID: " + errorCode);
							}
						}
						else {
							let errorCode = await error_code_generator(new Error(), "1071");
							api.session.revoke("Backend Error. Error ID: " + errorCode);
						}
					}
					else if (USER.error !== null) {
						let errorCode = await error_code_generator(new Error(), "1071");
						api.session.revoke("Backend Error. Error ID: " + errorCode);
					}
					else {
						let errorCode = await error_code_generator(new Error(), "1071");
						api.session.revoke("Backend Error. Error ID: " + errorCode);
					}
				}
				else if (event.connection.name === "NSKP-Preview") {
					api.samlResponse.setAttribute("Client Account Name", event.connection.name);
					api.samlResponse.setAttribute("User Account Type", "Employee");
				}
				else {
					api.samlResponse.setAttribute("Client Account Name", event.connection.name);
					//api.samlResponse.setAttribute("User Account Type", "N/A");
				}
				return;
			}
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Sync Administrative Privileges from Impartner to assign o-admin permissions for Partner Portal users.
    async function organization_admin_partner_portal_role_sync() {
        try {
            const axios = require("axios");
            if (event.client.name.includes("Netskope Partner Portal") || event.client.name === ("CIAM Dashboard")) {
				if (event.user.app_metadata.hasOwnProperty("birthright") && event.user.app_metadata.hasOwnProperty("entitlements") && (event.user.app_metadata.birthright.includes("Partner") || event.user.app_metadata.entitlements.includes("Partner"))) {
					// Backslash-escape \ and ' before embedding the email into Impartner's filter
					// expression. URL encoding via axios params protects transport, not the filter
					// language itself.
					const safeEmail = (event.user.email || "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
					await axios({
						method: "get",
						headers: {"Content-Type": "application/json"},
						url: "https://stage.impartner.live/api/objects/v1/User",
						params: {filter: "email='" + safeEmail + "'", fields: "email,id,Administrative_Privileges__cf"},
						auth: {username: event.secrets.impEmail, password: event.secrets.impPwd}
					})
					.then(async function(response) {
						try {
							let userCount = response.data.data.results.length;
							if (userCount >= 1) {
								let partner_user = response.data.data.results[0];
								// Impartner returns the field key with a lowercase first letter and null when empty.
								const privileges = Array.isArray(partner_user.administrative_Privileges__cf)
									? partner_user.administrative_Privileges__cf
									: [];
								const is_member_admin = privileges.includes("Member Administrator");

								// Mutate the shared permissions_state in place. The centralized commit at
								// the bottom of onExecutePostLogin will dedupe and write.
								const has_o_admin = permissions_state.current.includes("o-admin");

								if (is_member_admin) {
									if (!has_o_admin) {
										console.log("Assigning o-admin to user.");
										permissions_state.current.push("o-admin");
									} else {
										console.log("User already has o-admin. No change needed.");
									}
								}
								else {
									if (has_o_admin) {
										console.log("Removing o-admin from user.");
										const idx = permissions_state.current.indexOf("o-admin");
										if (idx !== -1) permissions_state.current.splice(idx, 1);
									} else {
										console.log("User is not a Member Administrator. Skipping.");
									}
								}
							}
							else {
								console.log("No matching user found. Skipping.");
							}
						}
						catch (error){
							let errorCode = await error_code_generator(new Error(), "1071");
							console.error("Backend Error. Error ID: " + errorCode);
						}
					})
					.catch(async function(error){
						let errorCode = await error_code_generator(new Error(), "1071");
						console.error("Backend Error. Error ID: " + errorCode);
					})
				}
			}
            else {
                return;
            }
        }
        catch(err) {
            let errorCode = await error_code_generator(new Error(), "1071");
            console.error("Backend Error. Error ID: " + errorCode);
            return;
        }
    }

    //Updates to users wtihin the NetskopeID table that need to be pushed on each login event.
    //We do this to make sure we capture changes to the entitlements and permissions fields.
    //
    // Reads from entitlement_state.current and permissions_state.current (the
    // shared mutable arrays the Block-* / o-admin helpers mutated) rather than
    // event.user.app_metadata, which is a start-of-action snapshot and would
    // miss any changes made by this action's helpers.
    async function sync_each_login() {
        if (event.connection.name === "NetskopeID") {
            var SYNC_EVERYTIME = {
                entitlements: [...new Set(entitlement_state.current)],
                permissions: [...new Set(permissions_state.current)],
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

    
    await set_federated_partner_portal_attributes();
    //console.log("Done 1")
    await get_partner_portal_user();
    //console.log("Done 2")
    await set_netskope_community_attributes();
    //console.log("Done 3")
    await get_netskope_community_user();
    //console.log("Done 4")
    await set_netskope_support_portal_attributes();
    //console.log("Done 5")
    await get_netskope_support_user();
    //console.log("Done 6")
    await set_netskope_academy_attributes();
    //console.log("Done 7")
    await organization_admin_partner_portal_role_sync();
    //console.log("Done 8")

    // Single, centralized commits of the array-valued app_metadata keys.
    // Helpers above mutate *_state.current in place; these blocks dedupe and
    // write once iff the final value differs from the start-of-action snapshot.
    // Replaces multiple racing setAppMetadata calls for the same key.
    const final_entitlements = [...new Set(entitlement_state.current)];
    const initial_entitlements_set = new Set(entitlement_state.initial);
    const entitlements_changed = final_entitlements.length !== initial_entitlements_set.size
        || final_entitlements.some(v => !initial_entitlements_set.has(v));
    if (entitlements_changed) {
        api.user.setAppMetadata("entitlements", final_entitlements);
    }

    const final_permissions = [...new Set(permissions_state.current)];
    const initial_permissions_set = new Set(permissions_state.initial);
    const permissions_changed = final_permissions.length !== initial_permissions_set.size
        || final_permissions.some(v => !initial_permissions_set.has(v));
    if (permissions_changed) {
        api.user.setAppMetadata("permissions", final_permissions);
    }

    await sync_each_login();

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
