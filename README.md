### Weekly Cron to Obtain Asset Information



```
cron-endpoint_asset_information.yml

```

> This script runs weekly cron at 

```
on:
  workflow_dispatch:
  schedule:
    # Minute 1 on Monday
    - cron: '1 * * * 1'

```
# Endpoint asset inventory

This script:
```
endpoint_asset_inventory.py
```
> congregates stack logs into a single ingest with 
- dict_keys(['automox', 'crowdstrike'])
- and values [hostname, os]


# Compatibility 

> python-version: ["3.8" ,"3.9", "3.10", "3.11", "3.12"]


