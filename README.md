# GCP-Shell

A repository for a Google Cloud Compute Provider to be used with QualiSystems' CloudShell.

This is a work in progress.

## Installation
* [QualiSystems CloudShell](http://www.qualisystems.com/products/cloudshell/cloudshell-overview/)


## Getting Started

1. Download the latest release (or download the whole project to create the latest package using [shellfoundry](https://github.com/QualiSystems/shellfoundry))
2. In the CloudShell Portal, import the shell into the Manage/Shells page
3. You'll need to provide a path to a Service account key json file which can be generated in the [GC console](https://console.cloud.google.com/apis/credentials).
4. Create a new Google Cloud Compute resource in the Inventory. Provide the path to the json file and the project name under which VMs will be created. 
5. Create Apps that are using this cloud provider.
6. Create a blueprint with one or more apps, and none or more subnets to connect the apps. 
7. Reserve the blueprint and let it deploy everything for you.

## License
[Apache License 2.0](https://github.com/QualiSystemslab/GCP-Shell/blob/master/LICENSE)