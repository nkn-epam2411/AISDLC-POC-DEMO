import os
import shutil
import zipfile
import base64
import requests
import json
import xml.etree.ElementTree as ET
from simple_salesforce import Salesforce

import logging
logging.basicConfig(level=logging.DEBUG)

# Logging for debugging
import http.client
http.client.HTTPConnection.debuglevel = 1

# Temporary directories
METADATA_DIR = "temp_metadata"
ZIP_FILE_NAME = "metadata_deployable.zip"

def clear_temp_metadata():
    if os.path.exists(METADATA_DIR):
        shutil.rmtree(METADATA_DIR)
    os.makedirs(METADATA_DIR)

# Step 1: Authenticate with Salesforce via Connected App
def login_to_salesforce(client_id, client_secret, sf_instance_url):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    TOKEN_URL = f"{sf_instance_url}/services/oauth2/token"
    response = requests.post(TOKEN_URL, headers=headers, data=body)
    if response.status_code == 200:
        auth_response = response.json()
        print("Logged in to Salesforce successfully")
        return auth_response["access_token"], auth_response["instance_url"]
    else:
        raise Exception(f"Failed to log in to Salesforce: {response.status_code} {response.text}")

# Step 1: Obtain Access Token
def get_access_token(client_id_a,client_secret_a,token_url_a):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "grant_type": "client_credentials",
         "client_id": client_id_a,
        "client_secret": client_secret_a,
    }
    response = requests.post(token_url_a, headers=headers, data=body)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.status_code} {response.text}")


# Step 2: Create a Conversation
def create_conversation(token, endpoint_url, assistant_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {"initialAssistantId": assistant_id}
    response = requests.post(f"{endpoint_url}/v1/conversations", headers=headers, json=body)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        raise Exception(f"Failed to create conversation: {response.status_code} {response.text}")


# Step 3: Ask the AI Assistant
def ask_assistant(token, endpoint_url, assistant_id, conversation_id, prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {"text": prompt, "conversationId": conversation_id}
    print("json body", body)
    response = requests.post(f"{endpoint_url}/v1/assistants/{assistant_id}/model", headers=headers, json=body)
    print("Raw Response:", response.text)
    if response.status_code == 200:
        ai_response = response.json()
        print("Raw AI Response:", ai_response)

        if "generated" in ai_response:
            try:
                parsed_response = json.loads(ai_response["generated"])
                print("Parsed AI Response:", parsed_response)
                return parsed_response
            except json.JSONDecodeError as e:
                raise Exception(f"Error parsing generated JSON: {e}, Raw Generated: {ai_response['generated']}")
        else:
            raise Exception("The 'generated' field is missing in the AI response.")
    else:
        raise Exception(f"Failed to ask assistant: {response.status_code} {response.text}")


# Step 4: Save Metadata Files
def save_metadata_files(ai_response):
    metadata_map = {
        "ApexClass": "classes/{name}.cls",
        "ApexClassMeta": "classes/{name}.cls-meta.xml",
        "ApexTrigger": "triggers/{name}.trigger",
        "ApexTriggerMeta": "triggers/{name}.trigger-meta.xml",
        "ApprovalProcess": "approvalProcesses/{name}.approvalProcess",
        "Queue": "queues/{name}.queue",
        "CustomMetadata": "customMetadata/{name}.md",
        "CustomObject": "objects/{name}.object",
        "CustomTab": "tabs/{name}.tab",
        "CustomApplication": "applications/{name}.app",
        "CustomApplicationComponent": "applicationComponents/{name}.appComponent",
        "CustomLabels": "labels/CustomLabels.labels-meta.xml",
        "FlexiPage": "flexipages/{name}.flexipage",
        "GlobalValueSet": "globalValueSets/{name}.globalValueSet-meta.xml",
        "QuickAction": "quickActions/{name}.quickAction",
        "LightningComponentBundle": "lwc/{name}",
        "Flow": "flows/{name}.flow",
        "Layout": "layouts/{name}.layout-meta.xml",
        "PermissionSet": "permissionsets/{name}.permissionset-meta.xml",
        "PageLayout": "layouts/{name}.layout-meta.xml",
        "PicklistValueSet": "globalValueSets/{name}.globalValueSet-meta.xml",
        "ReportType": "reportTypes/{name}.reportType-meta.xml"
    }

    for entry in ai_response["metadata"]:
        metadata_type = entry["type"]
        file_template = metadata_map.get(metadata_type)

        if metadata_type == "LightningComponentBundle":
            component_name = entry.get("name", "UnnamedComponent")
            # Convert component name to camelCase starting with a lowercase letter
            component_name = component_name[0].lower() + component_name[1:]
            component_dir = os.path.join(METADATA_DIR, "lwc", component_name)
            os.makedirs(component_dir, exist_ok=True)

            # Create .html file
            html_content = entry.get("htmlContent", "")
            with open(os.path.join(component_dir, f"{component_name}.html"), "w") as f:
                f.write(html_content)

            # Create .css file
            css_content = entry.get("cssContent", "")
            with open(os.path.join(component_dir, f"{component_name}.css"), "w") as f:
                f.write(css_content)

            # Create .js file
            js_content = entry.get("jsContent", "")
            with open(os.path.join(component_dir, f"{component_name}.js"), "w") as f:
                f.write(js_content)

            # Create .meta.xml file
            meta_content = entry.get("metaContent", "")
            with open(os.path.join(component_dir, f"{component_name}.js-meta.xml"), "w") as f:
                f.write(meta_content)
        elif file_template:
            file_path = os.path.join(METADATA_DIR, file_template.format(
                name=entry.get("name", "Unnamed"),
                objectName=entry.get("objectName", "UnknownObject")
            ))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(entry["content"])
            
            # Create .meta.xml file for ApexClass and ApexTrigger
            if metadata_type in ["ApexClass", "ApexTrigger"]:
                meta_file_template = metadata_map.get(metadata_type + "Meta")
                if meta_file_template:
                    meta_file_path = os.path.join(METADATA_DIR, meta_file_template.format(
                        name=entry.get("name", "Unnamed")
                    ))
                    meta_content = entry.get("metaContent", "")
                    with open(meta_file_path, "w") as f:
                        f.write(meta_content)
        else:
            print(f"Unsupported metadata type: {metadata_type}")


# Step 5: Generate package.xml
def generate_package_xml(ai_response):
    package_xml_header = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
"""
    package_xml_footer = """  <version>57.0</version>
</Package>"""

    metadata_types = {}

    # Process each metadata entry from AI response
    for entry in ai_response["metadata"]:
        metadata_type = entry["type"]
        name = entry["name"]

        # Handle CustomObject separately to extract fields and validation rules
        if metadata_type == "CustomObject":
            # Ensure proper CustomObject API name (e.g., Employee__c)
            if not name.endswith("__c"):
                name = f"{name}__c"

            # Add the CustomObject to metadata_types
            if metadata_type not in metadata_types:
                metadata_types[metadata_type] = []
            metadata_types[metadata_type].append(name)

            # Parse the CustomObject XML content to extract fields and validation rules
            custom_object_content = entry["content"]
            root = ET.fromstring(custom_object_content)

            # Extract <fields> and add to CustomField metadata
            for field in root.findall(".//{http://soap.sforce.com/2006/04/metadata}fields"):
                field_name = field.find("{http://soap.sforce.com/2006/04/metadata}fullName").text
                if "CustomField" not in metadata_types:
                    metadata_types["CustomField"] = []
                metadata_types["CustomField"].append(f"{name}.{field_name}")

            # Extract <validationRules> and add to ValidationRule metadata
            for validation_rule in root.findall(".//{http://soap.sforce.com/2006/04/metadata}validationRules"):
                rule_name = validation_rule.find("{http://soap.sforce.com/2006/04/metadata}fullName").text
                if "ValidationRule" not in metadata_types:
                    metadata_types["ValidationRule"] = []
                metadata_types["ValidationRule"].append(f"{name}.{rule_name}")

        # Other metadata types (e.g., PermissionSet)
        else:
            if metadata_type not in metadata_types:
                metadata_types[metadata_type] = []
            metadata_types[metadata_type].append(name)

    # Build package.xml body
    package_xml_body = ""
    for metadata_type, members in metadata_types.items():
        package_xml_body += f"  <types>\n"
        for member in members:
            package_xml_body += f"    <members>{member}</members>\n"
        package_xml_body += f"    <name>{metadata_type}</name>\n"
        package_xml_body += f"  </types>\n"

    # Combine header, body, and footer
    package_xml_content = package_xml_header + package_xml_body + package_xml_footer

    # Save package.xml to the correct location
    package_xml_path = os.path.join(METADATA_DIR, "package.xml")
    os.makedirs(os.path.dirname(package_xml_path), exist_ok=True)
    with open(package_xml_path, "w") as f:
        f.write(package_xml_content)
    print(f"Generated package.xml: {package_xml_path}")


# Step 6: Create ZIP package
def create_zip_package():
    # Remove existing ZIP file if present
    if os.path.exists(ZIP_FILE_NAME):
        os.remove(ZIP_FILE_NAME)

    # Create the ZIP package
    with zipfile.ZipFile(ZIP_FILE_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(METADATA_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, METADATA_DIR)
                zipf.write(file_path, arcname)
    
    # Verify the ZIP file
    if not os.path.exists(ZIP_FILE_NAME):
        raise Exception("ZIP file was not created successfully")
    print(f"Created ZIP package: {ZIP_FILE_NAME}")


# Step 7: Deploy metadata to Salesforce
def deploy_metadata(access_token, instance_url):
    # Read and encode the ZIP file
    with open(ZIP_FILE_NAME, "rb") as f:
        zip_content = f.read()
    
    # Encode ZIP file in base64
    base64_zip = base64.b64encode(zip_content).decode("utf-8")

    # Metadata API endpoint
    metadata_endpoint = f"{instance_url}/services/Soap/m/57.0"

    # Deploy SOAP request
    deploy_request_body = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://soap.sforce.com/2006/04/metadata">
        <soapenv:Header>
            <met:SessionHeader>
                <met:sessionId>{access_token}</met:sessionId>
            </met:SessionHeader>
        </soapenv:Header>
        <soapenv:Body>
            <met:deploy>
                <met:ZipFile>{base64_zip}</met:ZipFile>
                <met:DeployOptions>
                    <met:singlePackage>true</met:singlePackage>
                </met:DeployOptions>
            </met:deploy>
        </soapenv:Body>
    </soapenv:Envelope>
    """

    headers = {"Content-Type": "text/xml", "SOAPAction": "deploy"}
    response = requests.post(metadata_endpoint, data=deploy_request_body, headers=headers)

    if response.status_code == 200:
        print("Metadata deployment initiated successfully.")
        print("SOAP Response:", response.text)
    else:
        print(f"Failed to deploy metadata: {response.status_code}")
        print("SOAP Response:", response.text)


def upload_directory_to_github(issue_key, temp_metadata_dir, repo_owner, repo_name, github_token):
    # """
    # Upload all contents of a directory (files, folders, subfolders) to a new GitHub branch and publish the branch.
    # """
    # GitHub API Base URL
    github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    # Step 1: Get the default branch reference (usually "main" or "master")
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(f"{github_api_url}/git/ref/heads/main", headers=headers)

    print("GIT GET Response:", response.text)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch the default branch reference: {response.status_code} {response.text}")

    default_branch_data = response.json()
    sha_of_default_branch = default_branch_data['object']['sha']

    print(f"Default branch reference fetched successfully: {sha_of_default_branch}")

    # Step 2: Create a new branch from the default branch
    branch_name = f"feature/{issue_key}"
    payload = {
        "ref": f"refs/heads/{branch_name}",
        "sha": sha_of_default_branch
    }

    response = requests.post(f"{github_api_url}/git/refs", headers=headers, json=payload)
    if response.status_code != 201:
        raise Exception(f"Failed to create a new branch: {response.status_code} {response.text}")

    print(f"Branch {branch_name} created successfully.")

    # Step 3: Upload all files and folders from the temp_metadata_dir to the new branch
    for root, dirs, files in os.walk(temp_metadata_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_content = open(file_path, "rb").read()
            file_path_in_repo = os.path.relpath(file_path, temp_metadata_dir).replace("\\", "/")  # Relative path within the repo

            # Encode the file content to base64
            base64_content = base64.b64encode(file_content).decode("utf-8")
            payload = {
                "message": f"Adding {file_path_in_repo} for issue {issue_key}",
                "content": base64_content,
                "branch": branch_name
            }

            # Commit each file
            response = requests.put(f"{github_api_url}/contents/{file_path_in_repo}", headers=headers, json=payload)
            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to upload {file_path_in_repo}: {response.status_code} {response.text}")

    print(f"All files from {temp_metadata_dir} uploaded successfully to branch {branch_name}.")


    # URL of the newly created branch
    branch_url = f"https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}"
    print(f"Branch {branch_name} published successfully. URL: {branch_url}")
    return branch_url


# Main execution
# if __name__ == "__main__":
def process_jira(prompt, client_id_a, client_secret_a, token_url_a, endpoint_url, assistant_id, client_id, client_secret, sf_instance_url,issue_key,git_pat):
    try:

        # Clear the temp_metadata directory
        clear_temp_metadata()

        print("Fetching access token...")
        token = get_access_token(client_id_a,client_secret_a,token_url_a)

        print("Creating conversation...")
        conversation_id = create_conversation(token, endpoint_url, assistant_id)

        print("Querying AI assistant...")
        ai_response = ask_assistant(token, endpoint_url, assistant_id, conversation_id, prompt)

        print("Saving metadata files...")
        save_metadata_files(ai_response)

        print("Generating package.xml...")
        generate_package_xml(ai_response)

        # print("Creating ZIP package...")
        # create_zip_package()

        # print("Logging in to Salesforce...")
        # access_token, instance_url = login_to_salesforce(client_id, client_secret, sf_instance_url)

        # print("Deploying metadata to Salesforce...")
        # deploy_metadata(access_token, instance_url)

        print("Process completed successfully!")

        print("Uploading directory to GitHub...")
        github_branch_url = upload_directory_to_github(issue_key, METADATA_DIR, "nkn-boss", "MetadataCreationAI", git_pat)
        
        return github_branch_url

    except Exception as e:
        print(f"Error: {e}")
