# Project Emu
##### REST API Documentation

---

## Record Management

**Update Vendor**
<details>
 <summary><code>POST</code> <code>/api/internal/vendor/{vendor_id}</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | vendor_id | required | int  | The ID of the vendor you wish to update.  |

##### Data

Data Type :: `Form`

```
Enter data here
```


</details><br>

**Add a new Vendor**
<details>
 <summary><code>POST</code> <code>/api/internal/vendor/add</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Data

Data Type :: `Form`

```
Enter data here
```

</details><br>

**Delete a Vendor**
<details>
 <summary><code>POST</code> <code>/api/internal/vendor/{vendor_id}/delete</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | vendor_id | required | int  | The ID of the vendor you wish to delete.  |


</details><br>

**Delete a Vendor's Data**
<details>
 <summary><code>POST</code> <code>/api/internal/vendor/{vendor_id}/data/delete</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | vendor_id | required | int  | The ID of the vendor you wish to delete the data of.  |


</details><br>

**Update Component**
<details>
 <summary><code>POST</code> <code>/api/internal/component/{component_id}</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | component_id | required | int  | The ID of the component you wish to update.  |

##### Data

Data Type :: `Form`

```
Enter data here
```


</details><br>

**Delete a Component**
<details>
 <summary><code>POST</code> <code>/api/internal/component/{component_id}/delete</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | component_id | required | int  | The ID of the component you wish to delete.  |


</details><br>

**Update Vulnerability**
<details>
 <summary><code>POST</code> <code>/api/internal/vulnerability/{vulnerability_id}</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | vulnerability_id | required | int  | The ID of the vulnerability you wish to update.  |

##### Data

Data Type :: `Form`

```
Enter data here
```

</details><br>

**Delete a Vulnerability**
<details>
 <summary><code>POST</code> <code>/api/internal/vulnerability/{vulnerability_id}/delete</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Parameters

> | name      |  type     | data type               | description                                                           |
> |-----------|-----------|-------------------------|-----------------------------------------------------------------------|
> | vulnerability_id | required | int  | The ID of the vulnerability you wish to delete.  |


</details><br>

**Upload SBOM**
<details>
 <summary><code>POST</code> <code>/api/internal/sbom/upload</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Manage`

##### Data

Data Type :: `Form`

```
sbomFile={file}
```

</details><br>

## User Management

**Manage an Invited User**
<details>
 <summary><code>POST</code> <code>/api/internal/user/invited_users</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
action=accept
user=email@example.com
```

</details><br>

**Update User Roles**
<details>
 <summary><code>POST</code> <code>/api/internal/user/update_roles</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
NEED TO ADD
```

</details><br>

**Delete a User**
<details>
 <summary><code>POST</code> <code>/api/internal/user/delete_user</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
user_id=3179742972
```

</details><br>

**Reset a User's Password**
<details>
 <summary><code>POST</code> <code>/api/internal/user/reset_password</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
user_id=842853892
new_password=P@ssw0rd123
```

</details><br>

**Verify a User's Login Credentials**
<details>
 <summary><code>POST</code> <code>/api/internal/user/login</code></summary>

##### Authentication

JWT Required :: `No`

Permissions :: `None`

##### Data

Data Type :: `Form`

```
email=email@example.com
password=P@ssw0rd123
```

</details><br>

**Register a New User**
<details>
 <summary><code>POST</code> <code>/api/internal/user/register</code></summary>

##### Authentication

JWT Required :: `No`

Permissions :: `None`

##### Data

Data Type :: `Form`

```
name=John Doe
email=email@example.com
password=P@ssw0rd123
confirm_password=P@ssw0rd123
```

</details><br>

## Configurations

**Update the ThirdPartyTrust Integration**
<details>
 <summary><code>POST</code> <code>/api/internal/configuration/third_party_trust</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
api_key=ChangeMe
requirement_label=d7fd80sfj-fdhd8fdsj-fdhds8ff-fd8dfjfff
```

</details><br>

**Update the SSO Configuration**
<details>
 <summary><code>POST</code> <code>/api/internal/configuration/sso</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
OIDC_PROVIDER=Okta
PROVIDER_DOMAIN=test.okta.com
CLIENT_ID=ChangeMe
CLIENT_SECRET=ChangeMe
```

</details><br>

**Update the Logo**
<details>
 <summary><code>POST</code> <code>/api/internal/configuration/logo/upload</code></summary>

##### Authentication

JWT Required :: `Yes`

Permissions :: `Admin`

##### Data

Data Type :: `Form`

```
logoFile={file}
```

</details><br>