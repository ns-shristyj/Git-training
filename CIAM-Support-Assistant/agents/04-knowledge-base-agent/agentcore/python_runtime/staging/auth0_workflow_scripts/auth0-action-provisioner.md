# Auth0 Action: Provisioner

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Provisioner

- **Trigger(s):** pre-user-registration
- **Status:** built
- **Action ID:** 7a0de49a-a188-47bb-bb6d-b877f77e0681

**Script:**
```javascript
/**
* Handler that will be called during the execution of a PreUserRegistration flow.
*
* @param {Event} event - Details about the context and user that is attempting to register.
* @param {PreUserRegistrationAPI} api - Interface whose methods can be used to change the behavior of the signup.
*/
exports.onExecutePreUserRegistration = async (event, api) => {
    const axios = require("axios");
    const { v4: uuidv4 } = require("uuid");

    //Allow sign-ups via GUI
    if (event.client?.client_id === event.secrets.AUTH0_GUI_CID) {
        return;
    }

    //This function generates error codes based error stack trace.
    async function error_code_generator(e, code) {
        const regex = /\((.*):(\d+):(\d+)\)$/;
        const match = regex.exec(e.stack.split("\n")[1]);
        let uuid = uuidv4();
        let d = uuid.split("-");
        d[0] = code + (match && match[2] ? match[2].toString() : '') + (match && match[3] ? match[3].toString() : '');
        let newCode = d.join("-");
        return newCode;
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

    //This function is used to generated access tokens for teh Salesforce REST API.
    async function get_sfdc_token() {
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
        .catch(error => {
            return null;
        });
            return token;
    }

    //This function is used to retrieve Contact objects within Salesforce based on the user's email.
    async function get_sfdc_contact(email) {
        const token = await get_sfdc_token();
        if (token !== null) {
            let options = {
                method: 'GET',
                url: event.secrets.SF_AURL+"/services/data/v61.0/query?q=SELECT Id, IsDeleted, AccountId, LastName, FirstName, Name, Email, Title, CreatedDate FROM Contact WHERE Email='"+encodeURIComponent(email)+"' LIMIT 1",
                headers: {"Content-Type": "application/json", "Authorization": token}
            };
            let contact = await axios(options)
            .then(response => {
                if (response.data.totalSize >= 1) {
                    let record = response.data.records[0];
                    let contact = {"Id": record.Id??"","Email": record.Email??"","IsDeleted": record.IsDeleted??""};
                    if (contact.IsDeleted === true) {
                        return null;
                    }
                    else if (contact.Email !== email) {
                        return null;
                    }
                    else {
                        return contact;
                    }
                }
                else {
                    return null;
                }
            })
            .catch(error => {
                return null;
            })
            return contact;
        }
        else {
            return null;
        }
    }

    //Registrations are allowed.
    if (event.client?.metadata.hasOwnProperty('registrationsAllowed') && event.client?.metadata.registrationsAllowed === "true") {
        //Check to see if email is valid.
        let EMAIL_CHECK = await sanitizeEmail(event.user.email??"");
        if (EMAIL_CHECK.email !== null && EMAIL_CHECK.error === null) {
            const email = EMAIL_CHECK.email;
            //Registrations for Academy need to have a Contact object within Salesforce.
            if (event.client?.metadata.hasOwnProperty("entitlement") && event.client?.metadata.entitlement === "Academy") {
                const contact = await get_sfdc_contact(email);
                //If contact exists, proceed with sign-up.
                if (contact !== null && contact.Email === email) {
                    return;
                }
                //Else deny access.
                else {
                    return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Registration blocked for this application. Please reach out to training@netskope.com for access. "));
                }
            }
            //Registrations for other entitlements that allow registrations are allowed without additional checks.
            else {
                return;
            }
        }
        else {
            return(api.access.deny("Sign-Up Failed. Error ID: " + error_code_generator(new Error(), "1001"), "Sign-Up Failed."));
        }
    }
    // Registrations are blocked
    else if (event.client?.metadata.hasOwnProperty('registrationsAllowed') && event.client?.metadata.registrationsAllowed === "false") {
        // Determine contact email based on entitlement
        let contactEmail = "ciam@netskope.com";
        const entitlement = event.client?.metadata.entitlement;
        
        if (entitlement === "Support") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Community") {
            contactEmail = "community@netskope.com";
        } else if (entitlement === "Notification") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Partner" || entitlement === "Prime") {
            contactEmail = "partners@netskope.com";
            return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Please use the following form to request Partner Portal access: https://netskope.stage.partner-experience.com/partner/registration"));
        }
        
        return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Registration blocked for this application. Please reach out to "+contactEmail+" for access."));
    }
    // Registrations are blocked
    else if (!event.client?.metadata.hasOwnProperty('registrationsAllowed')) {
        // Determine contact email based on entitlement
        let contactEmail = "ciam@netskope.com";
        const entitlement = event.client?.metadata.entitlement;
        
        if (entitlement === "Support") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Community") {
            contactEmail = "community@netskope.com";
        } else if (entitlement === "Notification") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Partner" || entitlement === "Prime") {
            contactEmail = "partners@netskope.com";
            return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Please use the following form to request Partner Portal access: https://netskope.stage.partner-experience.com/partner/registration"));
        }
        
        return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Registration blocked for this application. Please reach out to "+contactEmail+" for access."));
    }
    // Registrations are blocked
    else {
        // Determine contact email based on entitlement
        let contactEmail = "ciam@netskope.com";
        const entitlement = event.client?.metadata.entitlement;
        
        if (entitlement === "Support") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Community") {
            contactEmail = "community@netskope.com";
        } else if (entitlement === "Notification") {
            contactEmail = "support@netskope.com";
        } else if (entitlement === "Partner" || entitlement === "Prime") {
            contactEmail = "partners@netskope.com";
            return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Please use the following form to request Partner Portal access: https://netskope.stage.partner-experience.com/partner/registration"));
        }
        
        return(api.access.deny("Registrations are not allowed for "+event.client?.name+" : "+ event.client?.client_id +".", "Registration blocked for this application. Please reach out to "+contactEmail+" for access."));
    }
}

```
