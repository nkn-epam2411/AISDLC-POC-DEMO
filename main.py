from flask import Flask, request, jsonify
import base64
from script import process_jira

app = Flask(__name__)

@app.route('/')
def home():
    return "Python REST API is running!"

@app.route('/deploy', methods=['POST'])
def deploy_metadata():
    try:
        # Parse the incoming JSON payload
        data = request.json
        prompt = data.get("prompt")
        client_id_a = data.get("client_id_a")
        client_secret_a = data.get("client_secret_a")
        token_url_a = data.get("token_url_a")
        endpoint_url = data.get("endpoint_url")
        assistant_id = data.get("assistant_id")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        sf_instance_url = data.get("sf_instance_url")
        issueKey = data.get("issueKey")

        # Log incoming data for debugging
        print(f"Received Prompt: {prompt}")

        # Call the main function in `script.py`
        deployment_url = process_jira(
            prompt,
            client_id_a, 
            client_secret_a, 
            token_url_a, 
            endpoint_url, 
            assistant_id, 
            client_id, 
            client_secret, 
            sf_instance_url,
            issueKey
        )

        # Return the deployment URL and encoded ZIP content
        return jsonify({
            "status": "success",
            "deployment_url": deployment_url
        }), 200

        # return jsonify({"status": "success", "deployment_url": deployment_url}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    # app.run(debug=True, host='https://aisdlc-poc-demo.onrender.com', port=5000)
