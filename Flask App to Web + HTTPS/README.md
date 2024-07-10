### TO-DO 

```
Fail2Ban:
- Currently Fail2Ban is blindly copied over the GitHub repository without being synced with the
 current Fail2Ban existing on the Ubuntu server. Similar function with copying the REPO over to the
 ubuntu server needs to be applied so the Fail2Ban database doesn't get overwritten.
```
### Fail2Ban: ban hosts that cause multiple authentication errors

```
Fail2Ban scans log files like /var/log/auth.log and bans IP addresses conducting too many failed login attempts. It does this by updating system firewall rules to reject new connections from those IP addresses, for a configurable amount of time. Fail2Ban comes out-of-the-box ready to read many standard log files, such as those for sshd and Apache, and is easily configured to read any log file of your choosing, for any error you wish.

Though Fail2Ban is able to reduce the rate of incorrect authentication attempts, it cannot eliminate the risk presented by weak authentication. Set up services to use only two factor, or public/private authentication mechanisms if you really want to protect services.

For more info on the service:
https://github.com/fail2ban/fail2ban
```
### Ansible: open-source IT automation engine

```
Ansible is an open source IT automation engine that automates provisioning, configuration management, application deployment, orchestration, and many other IT processes. It is free to use, and the project benefits from the experience and intelligence of its thousands of contributors.

It builds on the foundation of the open source project to create an end-to-end automation experience for cross-functional teams.
```

### Flask

We used Flask

### Terraform

To start up AWS Server

### NGINX / GUnicorn

^