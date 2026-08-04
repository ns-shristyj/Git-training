# Auth0 Action: ImPartner-Org-Admin-Sync

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### ImPartner-Org-Admin-Sync

- **Trigger(s):** event-stream
- **Status:** built
- **Action ID:** 119ae3ca-14d7-49cd-8ca4-99556b175f66

**Script:**
```javascript
/**
* Handler to be executed while processing events in an Event Stream.
* @param {Event} event - Details about the incoming event.
* @param {EventStreamAPI} api - Methods and utilities to define event stream processing.
*/
exports.onExecuteEventStream = async (event, api) => {
  // console.log("Event ID:", event.message.id);
  // console.log("Event Type:", event.message.type);

  // Sync the user's o-admin permission state to Impartner's Administrative_Privileges__cf:
  //   o-admin present in permissions → ensure "Member Administrator" is in the array
  //   o-admin absent  in permissions → ensure "Member Administrator" is not in the array
  // Other array values are preserved. If removing "Member Administrator" empties the array,
  // the field is set to null (Impartner's representation of "no values"). Only patches
  // Impartner when the membership of "Member Administrator" would actually change.
  async function update_impartner_administrative_privileges() {
    const axios = require("axios");
    const MEMBER_ADMIN = "Member Administrator";
    try {
      const user = event.message?.data?.object;
      const email = user?.email;
      const permissions = Array.isArray(user?.app_metadata?.permissions)
        ? user.app_metadata.permissions
        : [];

      if (!email) {
        console.log("No email on event.message.data.object. Skipping.");
        return false;
      }

      const shouldHaveMemberAdmin = permissions.includes("o-admin");

      // Backslash-escape \ and ' before embedding into Impartner's filter expression.
      const safeEmail = email.replace(/\\/g, "\\\\").replace(/'/g, "\\'");

      // Look up the user in Impartner to get id + current Administrative_Privileges__cf.
      const lookup = await axios({
        method: "get",
        headers: { "Content-Type": "application/json" },
        url: "https://stage.impartner.live/api/objects/v1/User",
        params: { filter: "email='" + safeEmail + "'", fields: "email,id,Administrative_Privileges__cf" },
        auth: { username: event.secrets.impEmail, password: event.secrets.impPwd }
      });

      const results = lookup?.data?.data?.results;
      if (!Array.isArray(results) || results.length === 0) {
        console.log("No matching Impartner user for " + email + ". Skipping.");
        return false;
      }

      const impartnerUser = results[0];
      // Impartner returns the field key with a lowercase first letter and null when empty.
      const currentPrivileges = Array.isArray(impartnerUser.administrative_Privileges__cf)
        ? impartnerUser.administrative_Privileges__cf
        : [];
      const hasMemberAdmin = currentPrivileges.includes(MEMBER_ADMIN);

      if (shouldHaveMemberAdmin === hasMemberAdmin) {
        return true;
      }

      let newPrivileges;
      if (shouldHaveMemberAdmin) {
        newPrivileges = currentPrivileges.concat([MEMBER_ADMIN]);
      }
      else {
        const filtered = currentPrivileges.filter(function (v) { return v !== MEMBER_ADMIN; });
        // Impartner expects null (not []) to clear the field.
        newPrivileges = filtered.length > 0 ? filtered : null;
      }

      await axios({
        method: "patch",
        headers: { "Content-Type": "application/json" },
        url: "https://stage.impartner.live/api/objects/v1/User/" + String(impartnerUser.id),
        auth: { username: event.secrets.impEmail, password: event.secrets.impPwd },
        data: { id: impartnerUser.id, Administrative_Privileges__cf: newPrivileges }
      });
      return true;
    }
    catch (err) {
      console.error("Failed to update Impartner Administrative_Privileges__cf: " + (err?.message ?? String(err)));
      return false;
    }
  }

  // Remove the "updated-via-dash" key from the user's app_metadata via the
  // Management API. The Event Stream API doesn't expose a way to mutate
  // app_metadata, so we have to go through Management. Sending {key: null}
  // inside app_metadata removes the field per the Auth0 Management API contract.
  async function clear_updated_via_dash_marker() {
    try {
      const ManagementClient = require("auth0").ManagementClient;
      const management = new ManagementClient({
        domain: event.secrets.domain,
        clientId: event.secrets.client_id,
        clientSecret: event.secrets.client_secret
      });

      const user = event.message?.data?.object;
      const userId = user?.user_id;
      const appMetadata = user?.app_metadata;

      if (!userId || !appMetadata) {
        console.log("No user_id or app_metadata on event. Skipping marker cleanup.");
        return;
      }

      if (!("updated-via-dash" in appMetadata)) {
        return;
      }

      await management.users.update(userId, {app_metadata:{"updated-via-dash": null}});
    }
    catch (err) {
      console.error("Failed to clear updated-via-dash marker: " + (err?.message ?? String(err)));
    }
  }

  if (JSON.stringify(event.message).includes("updated-via-dash")) {
    const updated = await update_impartner_administrative_privileges();
    if (updated) {
      console.log("Run cleanup.")
      await clear_updated_via_dash_marker();
    }
  }

  return;
};
```
