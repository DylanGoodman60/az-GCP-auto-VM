# Azure & GCP VM creation script 

*This project was a part of the Cloud Computing course at the University of Guelph*

## Usage

 $ python 3 Automate.py

refer to prompts from the program

## Requirements

* User must have Python3.8+ installed
* User must install commandline interface for [https://learn.microsoft.com/en-us/cli/azure/install-azure-cli](Azure) and [https://cloud.google.com/sdk/docs/install](GCP)
* User must login to Azure and gcp in current shell
    * $ az login
    * $ gcloud auth login

* For Azure, user must create a resource group
    * az group create --name $RESOURCE_GROUP_NAME

* For gcp, user must enable google compute API's on current project [https://console.cloud.google.com/](here), and complete initialization `$ glcoud init`

## Configuration options 

### Azure 

* name
* resource-group
* image
* location
* admin-username
* computer-name (OPTIONAL)
* os-disk-name (OPTIONAL)

#### Notes

* SSH key will be automatically generated in ~/.ssh
* If there are multiple VM's, the same key will be re-used once generated
* The user will be prompted to list which ports they would like open in both cases

### GCP

* name
* image
* image-project
* zone

