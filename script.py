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

# Configuration for AI and Salesforce
CLIENT_ID_A = "codemie-epmc-sfac"
CLIENT_SECRET_A = "bnyL3Y0KVjHAyK64Gj8VPWdInTPVaXlA"
TOKEN_URL_A = "https://keycloak.eks-core.aws.main.edp.projects.epam.com/auth/realms/codemie-prod/protocol/openid-connect/token"
ENDPOINT_URL = "https://codemie.lab.epam.com/code-assistant-api"
ASSISTANT_ID = "5a9644fb-45a2-4a4c-b3b0-04e56438e0b9"

SF_USERNAME = "nkn@tambolalwc.com"
SF_PASSWORD = "iit8bombay@"
SF_SECURITY_TOKEN = "your_security_token"

# Configuration for AI and Salesforce
CLIENT_ID = "3MVG9pe2TCoA1Pf7qdc9Ay2ASNuKSiV248U2sNLEXJ5lAttchijqXbgeyEn87fwA2YMmsnIgFPHM4eaDfWkEK"
CLIENT_SECRET = "63BE4CD37E7C8C124F1A50227F0418669A3722168A949BC4B58F8B067C38158B"
SF_INSTANCE_URL = "https://nkn-web-dev-ed.my.salesforce.com/"
TOKEN_URL = f"{SF_INSTANCE_URL}/services/oauth2/token"

# Temporary directories
METADATA_DIR = "temp_metadata"
ZIP_FILE_NAME = "metadata_deployable.zip"

# Step 1: Authenticate with Salesforce via Connected App
def login_to_salesforce():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(TOKEN_URL, headers=headers, data=body)
    if response.status_code == 200:
        auth_response = response.json()
        print("Logged in to Salesforce successfully")
        return auth_response["access_token"], auth_response["instance_url"]
    else:
        raise Exception(f"Failed to log in to Salesforce: {response.status_code} {response.text}")

# Step 1: Obtain Access Token
def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID_A,
        "client_secret": CLIENT_SECRET_A,
    }
    response = requests.post(TOKEN_URL_A, headers=headers, data=body)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.status_code} {response.text}")


# Step 2: Create a Conversation
def create_conversation(access_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    body = {"initialAssistantId": ASSISTANT_ID}
    response = requests.post(f"{ENDPOINT_URL}/v1/conversations", headers=headers, json=body)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        raise Exception(f"Failed to create conversation: {response.status_code} {response.text}")


# Step 3: Ask the AI Assistant
def ask_assistant(prompt, access_token, conversation_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    body = {"text": prompt, "conversationId": conversation_id}
    response = requests.post(f"{ENDPOINT_URL}/v1/assistants/{ASSISTANT_ID}/model", headers=headers, json=body)

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
        "CustomObject": "objects/{name}.object",
        "PermissionSet": "permissionsets/{name}.permissionset-meta.xml",
        "CustomLabel": "labels/CustomLabels.labels-meta.xml",
        "PageLayout": "layouts/{name}.layout-meta.xml",
        "PicklistValueSet": "globalValueSets/{name}.globalValueSet-meta.xml",
        "ReportType": "reportTypes/{name}.reportType-meta.xml",
    }

    for entry in ai_response["metadata"]:
        metadata_type = entry["type"]
        file_template = metadata_map.get(metadata_type)

        if file_template:
            file_path = os.path.join(METADATA_DIR, file_template.format(
                name=entry.get("name", "Unnamed"),
                objectName=entry.get("objectName", "UnknownObject")
            ))
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(entry["content"])
        else:
            print(f"Unsupported metadata type: {metadata_type}")


# Step 5: Generate package.xml

# def generate_package_xml(ai_response):
#     package_xml_header = """<?xml version="1.0" encoding="UTF-8"?>
# <Package xmlns="http://soap.sforce.com/2006/04/metadata">
# """
#     package_xml_footer = """  <version>57.0</version>
# </Package>"""

#     metadata_types = {}

#     for entry in ai_response["metadata"]:
#         metadata_type = entry["type"]
#         name = entry["name"]

#         # Adjust API names for metadata types
#         if metadata_type in ["CustomField", "ValidationRule"]:
#             # Fields and validation rules must include the object's API name
#             object_name = entry.get("objectName")
#             name = f"{object_name}.{name}"

#         # Ensure proper CustomObject API name (e.g., Employee__c)
#         if metadata_type == "CustomObject" and not name.endswith("__c"):
#             name = f"{name}__c"

#         if metadata_type not in metadata_types:
#             metadata_types[metadata_type] = []
#         metadata_types[metadata_type].append(name)

#     # Build package.xml body
#     package_xml_body = ""
#     for metadata_type, members in metadata_types.items():
#         package_xml_body += f"  <types>\n"
#         for member in members:
#             package_xml_body += f"    <members>{member}</members>\n"
#         package_xml_body += f"    <name>{metadata_type}</name>\n"
#         package_xml_body += f"  </types>\n"

#     package_xml_content = package_xml_header + package_xml_body + package_xml_footer
#     package_xml_path = os.path.join(METADATA_DIR, "package.xml")
#     os.makedirs(os.path.dirname(package_xml_path), exist_ok=True)
#     with open(package_xml_path, "w") as f:
#         f.write(package_xml_content)
#     print(f"Generated package.xml: {package_xml_path}")


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

# Step 7: Generate Prompt Dynamically
def generate_dynamic_prompt(summary, description):
    return f"""
    Summary: {summary}
    Description: {description}
    Generate a structured JSON response for Salesforce Metadata generation.
    Use this schema:
    {{
        "metadata": [
            {{
                "type": "CustomObject",
                "name": "string",
                "content": "string"
            }},
            {{
                "type": "PermissionSet",
                "name": "string",
                "content": "string"
            }}
        ]
    }}
    Only include the metadata that is explicitly described in the story.
    Populate the response based on the story details and metadata requirements.
    """


# Main execution
# if __name__ == "__main__":
def process_jira(summary, description):
    try:
        # jira_summary = "Create metadata for multiple configurations"
        # jira_description = """
        # - Create a CustomObject named "Employee".
        # - Add fields:
        #   1. Name (Text, 80 characters).
        #   2. Email (Email).
        # - Add a validation rule: Email must be unique.
        # - Create a Permission Set for Employee Management.
        # """

        # prompt = f"Summary: {jira_summary}\nDescription: {jira_description}"

         # Jira issue details
        jira_summary = "Create metadata for multiple configurations"
        jira_description = """
        - Create a CustomObject named "Employee".
        - Add fields:
          1. Name (Text, 80 characters).
          2. Email (Email).
        - Add a validation rule: Email must be unique.
        - Create a Permission Set for Employee Management, Where we have Read & Create & Edit access Employee object & to it's all the fields.
        """

        # Generate AI prompt
        prompt = generate_dynamic_prompt(summary, description)

        print("Fetching access token...")
        token = get_access_token()

        print("Creating conversation...")
        conversation_id = create_conversation(token)

        print("Querying AI assistant...")
        ai_response = ask_assistant(prompt, token, conversation_id)

        print("Saving metadata files...")
        save_metadata_files(ai_response)

        print("Generating package.xml...")
        generate_package_xml(ai_response)

        print("Creating ZIP package...")
        create_zip_package()

        print("Logging in to Salesforce...")
        access_token, instance_url = login_to_salesforce()

        print("Deploying metadata to Salesforce...")
        deploy_metadata(access_token, instance_url)

        print("Process completed successfully!")

        return "https://nkn-web-dev-ed.lightning.force.com/lightning/setup/DeployStatus/home"

    except Exception as e:
        print(f"Error: {e}")
