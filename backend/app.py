import os
from openai import OpenAI
import re
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

import gpt_rules

# Get the directory of app.py
app_dir = Path(__file__).parent

# Set template and static folders relative to the project structure
template_folder = app_dir.parent / 'frontend' / 'templates'
static_folder = app_dir.parent / 'frontend' / 'static'

# Initialize Flask app with custom template and static folder paths
app = Flask(__name__,
            template_folder=str(template_folder),
            static_folder=str(static_folder))

# Load environment variables from .env in the backend directory
load_dotenv(dotenv_path=app_dir / '.env')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory storage:
# daily_logs: { date_str: [meal1, meal2, ...] }
# Each meal: { "timestamp": <ISO timestamp>, "items": [food_item, ...] }
daily_logs = {}
# Conversation history for the current meal
conversation_history = []
# Settings conversation history (not used now)
settings_history = []
# Pending food items for the current meal (accumulated until confirmed)
pending_items = []

# Example user settings (not used in this update)
user_settings = {
    "name": "John Doe",
    "age": "",
    "email": "",
    "height": "",
    "weight": "",
    "theme": "light",
    "fontSize": "medium"
}

def parse_gpt_lines(gpt_reply):
    """
    Extracts item details from final summary lines.
    Expected format per line:
      <food name> (<quantity> <size>), <protein> g protein, <carbs> g carbs, <fat> g fat, <calories> cals
    Returns a list of dictionaries.
    """
    items = []
    pattern = re.compile(
        r"^(.*?)\s*\(\s*([^\)]+)\s*\),\s*(\d+)\s*g protein,\s*(\d+)\s*g carbs,\s*(\d+)\s*g fat,\s*(\d+)\s*cals",
        re.IGNORECASE
    )
    for line in gpt_reply.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            food_name = match.group(1).strip()
            quantity_size = match.group(2).strip()
            protein = int(match.group(3))
            carbs = int(match.group(4))
            fat = int(match.group(5))
            calories = int(match.group(6))
            items.append({
                "food": f"{food_name} ({quantity_size})",
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "calories": calories
            })
    return items

def check_log_intent(gpt_reply):
    return "user wants to log the meal" in gpt_reply.lower()

def build_html_table(items):
    """
    Builds an HTML table from a list of food items.
    """
    total_protein = sum(i["protein"] for i in items)
    total_carbs = sum(i["carbs"] for i in items)
    total_fat = sum(i["fat"] for i in items)
    total_calories = sum(i["calories"] for i in items)
    table_html = """
    <table class="nutrition-table">
      <thead>
        <tr>
          <th>Ingredient</th>
          <th>Protein (g)</th>
          <th>Carbs (g)</th>
          <th>Fat (g)</th>
          <th>Calories</th>
        </tr>
      </thead>
      <tbody>
    """
    for i in items:
        table_html += f"""
        <tr>
          <td>{i["food"]}</td>
          <td>{i["protein"]} g</td>
          <td>{i["carbs"]} g</td>
          <td>{i["fat"]} g</td>
          <td>{i["calories"]} cals</td>
        </tr>
        """
    table_html += f"""
      </tbody>
      <tfoot>
        <tr>
          <th>Totals</th>
          <th>{total_protein} g</th>
          <th>{total_carbs} g</th>
          <th>{total_fat} g</th>
          <th>{total_calories} cals</th>
        </tr>
      </tfoot>
    </table>
    """
    return table_html.strip()

def get_followup_question(meal_summary):
    """
    Uses GPT to generate a dynamic, succinct follow-up question based on the meal summary.
    The question should ask:
    "Should I log this meal or do you want to add more food?"
    """
    prompt = (
        f"Based on the following meal summary:\n{meal_summary}\n"
        "Generate a brief follow-up question asking: 'Should I log this meal or do you want to add more food?'"
    )
    messages = [{"role": "system", "content": prompt}]
    response = client.chat.completions.create(model="gpt-4o-mini",
    messages=messages,
    temperature=0.5)
    question = response.choices[0].message.content.strip()
    return question

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/history")
def history():
    return render_template("history.html")

# Remove settings page per request; we're focusing on food logging and history

@app.route("/ask", methods=["POST"])
@app.route("/ask", methods=["POST"])
def ask():
    global pending_items, conversation_history
    data = request.json
    user_message = data.get("message", "").strip()

    conversation_history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": gpt_rules.SYSTEM_PROMPT}] + conversation_history

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )
        gpt_reply = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": gpt_reply})

        if check_log_intent(gpt_reply):
            date_str = datetime.now().strftime("%Y-%m-%d")
            meal_entry = {"timestamp": datetime.now().isoformat(), "items": pending_items.copy()}
            daily_logs.setdefault(date_str, []).append(meal_entry)
            pending_items.clear()
            conversation_history = []
            return jsonify({"reply": "Meal logged successfully!", "needsConfirmation": False})
        else:
            items = parse_gpt_lines(gpt_reply)
            if items:
                pending_items.extend(items)
                table_output = build_html_table(pending_items)
                meal_summary = "\n".join([i["food"] for i in pending_items])
                followup_question = get_followup_question(meal_summary)
                combined_reply = f"{table_output}\n\n{followup_question}"
                return jsonify({"reply": combined_reply, "needsConfirmation": True})
            else:
                return jsonify({"reply": gpt_reply, "needsConfirmation": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_history", methods=["GET"])
def get_history():
    result = {}
    for day, meals in daily_logs.items():
        all_items = []
        for meal in meals:
            all_items.extend(meal["items"])
        total_calories = sum(i.get("calories", 0) for i in all_items)
        total_protein = sum(i.get("protein", 0) for i in all_items)
        total_carbs = sum(i.get("carbs", 0) for i in all_items)
        total_fat = sum(i.get("fat", 0) for i in all_items)
        result[day] = {
            "calories": total_calories,
            "protein": total_protein,
            "carbs": total_carbs,
            "fat": total_fat,
            "items": all_items
        }
    return jsonify(result)

@app.route("/get_user_settings", methods=["GET"])
def get_user_settings():
    return jsonify(user_settings)

if __name__ == "__main__":
    app.run(debug=True)
