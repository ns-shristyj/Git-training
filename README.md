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


# Runs the following Script 

```
- name: Run endpoint-asset-information Script
      run: |
        python endpoint_asset_information.py

```

# Compatibility 

> python-version: ["3.8" ,"3.9", "3.10", "3.11", "3.12"]


