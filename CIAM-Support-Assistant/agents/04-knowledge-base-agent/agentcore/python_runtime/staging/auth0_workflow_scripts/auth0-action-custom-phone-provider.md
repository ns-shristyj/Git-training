# Auth0 Action: Custom Phone Provider

> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)
> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.

### Custom Phone Provider

- **Trigger(s):** custom-phone-provider
- **Status:** built
- **Action ID:** 0407a44e-e7b5-445e-8f77-12b2dace1304

**Script:**
```javascript
/**
 * Auth0 Custom Phone Provider Action
 * Sends OTP codes via AWS End User Messaging Notify (SendNotifyTextMessage)
 *
 * Scope: only handles message_type "otp_verify" and "otp_enroll", the only
 * types that carry event.notification.code. Notify currently only supports
 * the CODE_VERIFICATION use case, so other message types (blocked_account,
 * change_password, password_breach) cannot be sent via Notify at all — they
 * arrive as free-form text (event.notification.as_text) with no code, and
 * Notify has no template mechanism for arbitrary text. Those are dropped
 * here with a clear reason rather than silently failing on "missing code."
 *
 * Auth flow: the credentials in secrets belong to an IAM user/entity that
 * can only sts:AssumeRole into auth0_access_role (see Terraform). This
 * Action assumes that role via @aws-sdk/client-sts (v3, allowlisted on
 * node22) to get short-lived STS creds, then signs the SendNotifyTextMessage
 * call with those using aws4 — consistent with the pattern used by other
 * Auth0 Actions in this tenant. No long-lived creds with direct sms-voice
 * permissions are used. SendNotifyTextMessage itself has no v3 client
 * available in this runtime, so it's still hand-signed.
 *
 * Required secrets:
 *   AWS_ACCESS_KEY_ID       IAM user creds — sts:AssumeRole only
 *   AWS_SECRET_ACCESS_KEY
 *   AWS_REGION              e.g. "us-east-1"
 *   ROLE_ARN                arn of auth0_access_role
 *   ROLE_SESSION_NAME       e.g. "auth0-notify-action" (optional, has default)
 *   NOTIFY_CONFIGURATION_ID e.g. "nc-1234567890abcdef0"
 *   NOTIFY_TEMPLATE_ID      e.g. "notify-code-verification-english-001"
 *
 * NOTE: host/service values below are best-inference from the pinpoint-sms-voice-v2
 * service model. Confirm with:
 *   import botocore.session
 *   session = botocore.session.get_session()
 *   client = session.create_client('pinpoint-sms-voice-v2', region_name='us-east-1')
 *   print(client.meta.endpoint_url, client.meta.service_model.signing_name)
 * and update SERVICE_HOST_PREFIX / SIGNING_SERVICE below if they differ.
 */

const { STSClient, AssumeRoleCommand } = require('@aws-sdk/client-sts');
const aws4 = require('aws4');

const SERVICE_HOST_PREFIX = 'sms-voice'; // verify against botocore endpoint_url
const SIGNING_SERVICE = 'sms-voice';     // verify against botocore signing_name
const SEND_NOTIFY_PATH = '/v1/sms-voice/notify/message'; // verify against actual request

// Only these message types carry a `code` and map to a CODE_VERIFICATION template.
const SUPPORTED_MESSAGE_TYPES = ['otp_verify', 'otp_enroll'];

exports.onExecuteCustomPhoneProvider = async (event, api) => {
  const { recipient, delivery_method, code, message_type } = event.notification;

  if (delivery_method !== 'text') {
    return api.notification.drop(`Unsupported delivery_method: ${delivery_method}`);
  }

  if (!SUPPORTED_MESSAGE_TYPES.includes(message_type)) {
    return api.notification.drop(
      `message_type "${message_type}" has no code and is not supported via AWS Notify (CODE_VERIFICATION only)`
    );
  }

  if (!recipient) {
    return api.notification.drop('Missing recipient in notification payload');
  }

  if (!code) {
    return api.notification.drop(`Expected code for message_type "${message_type}" but none was present`);
  }

  const region = event.secrets.AWS_REGION;

  // Step 1: assume the role to get short-lived STS credentials
  let stsCreds;
  try {
    const stsClient = new STSClient({
      region,
      credentials: {
        accessKeyId: event.secrets.AWS_ACCESS_KEY_ID,
        secretAccessKey: event.secrets.AWS_SECRET_ACCESS_KEY,
      },
    });

    const assumed = await stsClient.send(new AssumeRoleCommand({
      RoleArn: event.secrets.ROLE_ARN,
      RoleSessionName: event.secrets.ROLE_SESSION_NAME || 'auth0-notify-action',
      DurationSeconds: 900, // minimum; credential is used once per invocation
    }));

    stsCreds = {
      accessKeyId: assumed.Credentials.AccessKeyId,
      secretAccessKey: assumed.Credentials.SecretAccessKey,
      sessionToken: assumed.Credentials.SessionToken,
    };
  } catch (err) {
    console.error(`AssumeRole failed: ${err.message}`);
    // v3 errors expose the AWS error code as err.name, not err.code
    const retryable = err.name === 'ThrottlingException' || err.$metadata?.httpStatusCode === 429;
    return retryable
      ? api.notification.retry(err.message)
      : api.notification.drop(err.message);
  }

  // Step 2: sign SendNotifyTextMessage with the assumed-role credentials
  const host = `${SERVICE_HOST_PREFIX}.${region}.amazonaws.com`;

  const requestBody = JSON.stringify({
    NotifyConfigurationId: event.secrets.NOTIFY_CONFIGURATION_ID,
    DestinationPhoneNumber: recipient, // expects E.164
    TemplateId: event.secrets.NOTIFY_TEMPLATE_ID,
    TemplateVariables: { code },
  });

  const signOpts = {
    host,
    path: SEND_NOTIFY_PATH,
    service: SIGNING_SERVICE,
    region,
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-amz-json-1.0',
      'X-Amz-Target': 'PinpointSMSVoiceV2.SendNotifyTextMessage',
    },
    body: requestBody,
  };

  // aws4 signs the security token into the request when sessionToken is present
  // on the credentials object, adding X-Amz-Security-Token automatically.
  aws4.sign(signOpts, stsCreds);

  try {
    const response = await fetch(`https://${host}${SEND_NOTIFY_PATH}`, {
      method: 'POST',
      headers: signOpts.headers,
      body: requestBody,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      const retryable = response.status === 429 || response.status >= 500;

      console.error(`SendNotifyTextMessage failed (${response.status}): ${errorBody}`);

      return retryable
        ? api.notification.retry(errorBody)
        : api.notification.drop(errorBody);
    }

    const { MessageId } = await response.json();
    console.log(`Notify SMS sent successfully. MessageId: ${MessageId}, message_type: ${message_type}`);
  } catch (err) {
    console.error(`SendNotifyTextMessage request error: ${err.message}`);
    return api.notification.retry(err.message);
  }
};
```
