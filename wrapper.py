import os
from time import sleep
from flask import Flask, request, jsonify
from openai import OpenAI
from flask_cors import CORS, cross_origin
from dotenv import load_dotenv
import requests
from io import BytesIO

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Init client
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/create", methods=["POST"])
@cross_origin(supports_credentials=True)
def create():

    data = request.json
    course_name = data.get("course_name", "")
    file_paths = data.get("file_paths", [])

    file_ids = []
    for file_path in file_paths:
        file_response = requests.get(file_path)
        file_object = BytesIO(file_response.content)
        file_object.seek(0)
        filename = file_path.split("/")[-1]
                                  
        file = client.files.create(
            file=(filename, file_object),
            purpose="assistants"
        )
        file_ids.append(file.id)
    
    assistant = client.beta.assistants.create(
        name=f"{course_name}",
        instructions="You are a teacher who fetch goals for the specified course",
        tools=[{"type": "retrieval"}],
        model="gpt-4-1106-preview",
        file_ids = file_ids
    )

    thread = client.beta.threads.create()

    prompt = f"What are the learning goals for the course {course_name}"

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Check if the Run requires action 
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id, run_id=run.id
        )
        print(f"Run status: {run_status.status}")
        if run_status.status == "completed":
            break
        sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    response = messages.data[0].content[0].text.value

    print(f"Assistant response: {response}")
    return jsonify({"assistant_id": assistant.id, "goals": response})

@app.route("/gen_questions", methods=["POST"])
@cross_origin(supports_credentials=True)
def gen_questions():
    data = request.json
    assistant_id = data.get("assistant_id", "")
    thread_id = data.get("thread_id")
    ques_num = data.get("ques_num", "")
    ques_type = data.get("ques_type", "")
    ques_focus = data.get("ques_focus", "")
    goals = data.get("goals", "")

    prompt = f"Generate {ques_num} questions of type {ques_type} with focus on {ques_focus} for the goal- {goals}"
    print(f"Received prompt: {prompt} for thread ID: {thread_id}")

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id, 
        assistant_id=assistant_id
    )

    # Check if the Run requires action 
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )
        print(f"Run status: {run_status.status}")
        if run_status.status == "completed":
            break
        sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    response = messages.data[0].content[0].text.value

    print(f"Assistant response: {response}")
    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)