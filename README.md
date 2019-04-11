# GCP-Shell

A repository for a Google Cloud Compute Provider to be used with QualiSystems' CloudShell.

This is a work in progress.

## Installation
First, make sure that you have CloudShell installed.
* [QualiSystems CloudShell](http://www.qualisystems.com/products/cloudshell/cloudshell-overview/)


## Getting Started

1. Download the latest release (or download the whole project to create the latest package using [shellfoundry](https://github.com/QualiSystems/shellfoundry))
2. In the CloudShell Portal, import the shell into the Manage/Shells page
3. You'll need to provide a path to a Service account key json file which can be generated in the [GC console](https://console.cloud.google.com/apis/credentials).
4. Create a new Google Cloud Compute resource in the Inventory. Provide the path to the json file and the project name under which VMs will be created. 
5. Create Apps that are using this cloud provider (see the deployment options below).
6. Create a blueprint with one or more apps, and none or more subnets to connect the apps. 
7. Reserve the blueprint and let it deploy everything for you.

## Supported deployment paths
You can use one of the following deployment paths:

1. **Google Cloud Custom VM** - Create a single VM instance from scratch. 
 You'll need to provide the relevant information, like the image project and image id.
 To get this information, use the GC Console to create a new VM instance, then choose the relevant boot dist.
 After selecting it, you can click on the 'command line' link at the bottom of the page, to see which values are being used.
 
2. **Google Cloud VM from Template** - Create a single VM instance from an existing template.
 If you have an existing template that you've created in the GC Console, you'll be able to provide the name of the template with this option, to deploy a new instance from this template.


## License
[Apache License 2.0](https://github.com/QualiSystemslab/GCP-Shell/blob/master/LICENSE)