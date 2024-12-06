from flask import Flask, request, jsonify
from script import process_jira

app = Flask(__name__)

@app.route('/')
def home():
    return "Python REST API is running!"

@app.route('/deploy', methods=['POST'])
def deploy_metadata():
    # Parse incoming JSON request
    data = request.json
    jira_summary = data.get("jira_summary")
    jira_description = data.get("jira_description")

    try:
        # Call your script's function
        deployment_url = process_jira(jira_summary, jira_description)
        return jsonify({"status": "success", "deployment_url": deployment_url}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=True, host='https://aisdlc-poc-demo.onrender.com', port=5000)
