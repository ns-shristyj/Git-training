# Looker Studio Dashboard 
v 0.2


## Exporting Complete Data

> Automox, Crowdstrike, Neskope, Intune, Kandji

```
python main.py     # main function -- performs full API pull and Transforms.

```


#### Looker Studio Import.


Transformed exports can be found here: 

* Extract_Scripts/out_data/kandji.json # raw kandji data
* Extract_Scripts/out_data/intune.json # raw intune data
* missing/intune_missing.json # missing stacks for intune comparison
* missing/kandji_missing.json # missing stacks for kandji comparison 
* volv_output/aug_intune_2.json # Stack events for Intune Comparison
* volv_output/aug_kandji_2.json # Stack events for Kandji Comparison 




# Testing Framework

``` 
python test_dryRun.py # generates arbitrary test data to test transform function accuracy. 


AutoKandji PASSED
AutoTune PASSED
CrowdKandji PASSED
CrowdTune PASSED
NetKandji PASSED
NetTune PASSED
-------------------------
Crowdstrike PASSED
Automox PASSED
Netskope PASSED

```

