import os, base64
from dotenv import load_dotenv

# explicitly point at the file named " .env" (leading space + .env)
load_dotenv(dotenv_path=" .env", override=True)

from flask import Flask, request, jsonify
from openai import OpenAI

# debug print to confirm we actually loaded the right key
print("DEBUG — OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

@app.route("/api/evaluate", methods=["POST"])
def evaluate_image():
    file      = request.files["image"]
    filepath  = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    with open(filepath, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    res = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role":"user",
            "content":[
                {
                  "type":"text",
                  "text":"Evaluate the quality of this clothing item based on visible stitching, fabric texture, brand indicators, and design. Return a score out of 100 and a short explanation."
                },
                {
                  "type":"image_url",
                  "image_url":{"url":f"data:image/jpeg;base64,{img_b64}"}
                }
            ]
        }]
    )

    os.remove(filepath)
    return jsonify({"result":res.choices[0].message.content})

if __name__=="__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(port=5000, debug=True)
