# CIS*4010 goodmand@uoguelph.ca 1102172
import re
import subprocess
import os
from datetime import datetime
import getpass
import json

required_azure_variables = ["name", "resource-group", "image", "location", "admin-username"]
optional_azure_variables = ["computer-name", "os-disk-name"]
required_gcp_variables = ["name", "image", "imageproject", "zone"]

# extract information from conf files
def parse_conf(filename):
    fp = open(filename)
    data = [x for x in fp.read().split("\n")]

    conf_arr = []
    for d in data:
        if '[' in d: # seen label, add new dictionary with vm info
            conf_arr.append({'label': d})
        elif '=' in d: # ignore empty strings
            conf_arr[-1][d.split(" = ")[0]] = d.split(" = ")[1]

    return conf_arr

# return false if validation fails
def validate_conf(data):
    vm_number = 1
    for entry in data:
        # verify VM TAG follows format [(azure|gcp)01-09]
        _, label = next(iter(entry.items()))
        pattern = r"\[(azure|gcp)(0[1-{}])\]".format(vm_number)
        if re.match(pattern, label) is None:
            print("Invalid VM tag: " + label)
            print("Ensure name and number are correct")
            return False
        vm_number += 1

    # verify all required tags exist
    if "azure" in label:
        for var in required_azure_variables:
            if var not in entry:
                print("Invalid Configuration. Variable " + var + " is required.")
                return False

    return True

def create_azure_vm(vm_data):
    # CONFIRM the user is logged in
    if subprocess.run(["az", "account", "list"], capture_output=True, text=True).returncode != 0:
        print("You may not be logged in. Please before use:")
        print("  $ az login")
        return False

    # generate password
    pwd = ''
    while(not validate_password(pwd)):
        pwd = input("Enter an admin password, 12-123 length, at least one lowercase, uppercase, digit and special character:\n")

    # BASE COMMAND for AZURE VM
    create_vm_command = [
        "az", 
        "vm", 
        "create", 
        "--generate-ssh-keys",
        "--admin-password",
        pwd
    ]

    # ADD more commands if they are required or optional
    for name, value in vm_data.items():
        if name in required_azure_variables or name in optional_azure_variables:
            create_vm_command.append("--" + name)
            create_vm_command.append(value)
    
    # PRINT out command about to executed
    print(f"\nCreating Azure VM... CLI command:")
    for cmd in create_vm_command:
        if cmd[0] == '-':
            print("")
            print(cmd, end="")
        else:
            print(" " + cmd, end="")
    print("\n")

    # CONFIRM user wants to create above VM
    confirm = input("\nConfirm creation of a VM with the above spec? (Y/n)\n").lower()
    if confirm not in ['y', 'yes']:
        print("Aborting...")
        return False
    
    # Check for resource group, help and exit on doesn't exist
    resource_cmd = ["az", "group", "show", "--resource-group", vm_data['resource-group']]
    result_1 = subprocess.run(resource_cmd, capture_output=True, text=True)
    if result_1.returncode != 0:
        print(f"Resource group {vm_data['resource-group']} could not be found! Please create one with the following command:")
        print(f"  $ az group create --name {vm_data['resource-group']} --location canadacentral")
        return False

    # CREATE VM and print info on success
    print("Creating VM...")
    result = subprocess.run(create_vm_command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to create VM! Please see below error message.")
        print(result.stderr)
        return False
    
    print("\nVM created successfully!")
    open_ports = input("Would you like to open ports? (Y/n)").lower()
    if open_ports in ['y', 'yes']:
        ports = input("Please indicate which ports you would like open via comma-separated values (eg: 80,443):\n")
        if ports:
            port_result = subprocess.run(
                ["az", "vm", "open-port", "-g", vm_data['resource-group'], "-n", vm_data['name'], "--port", ports],
                capture_output=True,
                text=True
            )

        if port_result.returncode != 0:
            print("Failed to open ports! Please specify correctly with comma-separated integers from 0-65353")
            return False

    print("\nVM creation info:")
    for key, value in json.loads(result.stdout).items():
        print(f"  {key}: {value}")
    print("\n")

    # write VM info to file on success
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d:%H:%M:%S")

    f = open("VM_creation_" + formatted_datetime, "w")
    f.write("Date Stamp: " + formatted_datetime + "\n")
    f.write("System Admin Name: " + getpass.getuser() + "\n")
    for name, value in vm_data.items():
        f.write(name + ": " + value + "\n")
    f.write("status: " + json.loads(result.stdout).get('powerState') + "\n")

    # SAVE azure conf file
    subprocess.run(["cp", "Azure.conf", "Azure_" + formatted_datetime + ".conf"])
    return True

def create_gcp_vm(vm_data):
    # Check if user is logged in
    result = subprocess.run(['gcloud', 'auth', 'list', '--format=json'], capture_output=True, text=True)
    if result.returncode == 0:
        auth_info = json.loads(result.stdout)
        if not bool(auth_info):
            print("You are not logged in. Please do so and select a project with gcloud login, then gcloud init to setup")
            return False
    else:
        print("You are not logged in. Please do so and select a project with gcloud login, then gcloud init to setup")
        return False

    # BASE COMMAND for AZURE VM
    create_vm_command = [
        "gcloud", 
        "compute", 
        "instances", 
        "create",
        vm_data['name']
    ]

    # ADD more commands if they are required or optional
    for name, value in vm_data.items():
        if name in required_gcp_variables and name != "name":
            if name == "imageproject":
                name = "image-project"
            create_vm_command.append("--" + name)
            create_vm_command.append(value)

    # OPEN PORTS
    open_port_80 = ["gcloud", "compute", "firewall-rules", "create", "tcp-rule-http", "--allow=tcp:80"]
    open_port_443 = ["gcloud", "compute", "firewall-rules", "create", "tcp-rule-https", "--allow=tcp:443"]

    port_80 = input("Would you like to open port 80 (Y/n)?\n").lower()
    port_443 = input("Would you like to open port 443 (Y/n)?\n").lower()
    
    if port_80 in ['y', 'yes'] or port_443 in ['y', 'yes']:
        subprocess.run(open_port_80, capture_output=True, text=True)
        subprocess.run(open_port_443, capture_output=True, text=True)
        create_vm_command.append("--tags")
        if port_80 in ['y', 'yes'] and port_443 in ['y', 'yes']:
            create_vm_command.append("tcp-rule-http,tcp-rule-https")
        elif port_80 in ['y','yes']:
            create_vm_command.append("tcp-rule-http")
        elif port_443 in ['y','yes']:
            create_vm_command.append("tcp-rule-https")

    # PRINT out command about to executed
    print(f"CLI command:")
    for cmd in create_vm_command:
        if cmd[0] == '-':
            print("")
            print(cmd, end="")
        else:
            print(" " + cmd, end="")
    print("\n")

    # CONFIRM user wants to create above VM
    confirm = input("Confirm creation of a VM with the above spec? (Y/n)\n").lower()
    if confirm not in ['y', 'yes']:
        print("Aborting...")
        return False


    # CREATE VM and print info on success
    print("Creating VM...")
    result = subprocess.run(create_vm_command, capture_output=True, text=True)

    if result.returncode != 0:
        print("Failed to create VM! Please see below error message.")
        print(result.stderr)
        return False
    
    print("\nVM created successfully!")
    print("VM Creation info:")
    print(result.stdout)

    # write VM info to file on success
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d:%H:%M:%S")

    f = open("VM_creation_" + formatted_datetime, "w")
    f.write("Date Stamp: " + formatted_datetime + "\n")
    f.write("System Admin Name: " + getpass.getuser() + "\n")
    for name, value in vm_data.items():
        f.write(name + ": " + value + "\n")
    if "RUNNING" in result.stdout:
        f.write("Status: RUNNING")

    # SAVE azure conf file
    subprocess.run(["cp", "gcp.conf", "gcp_" + formatted_datetime + ".conf"])

    return True

def validate_password(pwd):
    if not 12 <= len(pwd) <= 123: # length
        return False
    if not re.search(r'[a-z]', pwd): # lowercase
        return False
    if not re.search(r'[A-Z]', pwd): # uppercase
        return False
    if not re.search(r'\d', pwd): # digit
        return False
    if not re.search(r'[!@#$%^&*()\-_=+{};:,<.>]', pwd): # special character
        return False

    return True

def main():
    if not os.path.exists("Azure.conf") or not os.path.exists("gcp.conf"):
        print("conf files not found!")
        return

    az_data = parse_conf("Azure.conf")
    gcp_data = parse_conf("gcp.conf")
    
    if not validate_conf(az_data) or not validate_conf(gcp_data):
        print("Validation failed. Exiting...")
        return

    for vm in az_data:
        print("Create New Azure VM..\n")
        if not create_azure_vm(vm):
            return

    for vm in gcp_data:
        print("Create New GCP VM..\n")
        if not create_gcp_vm(vm):
            return

if __name__ == "__main__":
    main()
