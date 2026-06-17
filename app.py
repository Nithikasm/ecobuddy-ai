from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['DATABASE'] = 'ecobuddy.db'
app.secret_key = "ecobuddy_secret_key"


def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Added session_id TEXT to the schema layout
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eco_score INTEGER,
            score_grade TEXT,
            annual_emissions INTEGER,
            monthly_average INTEGER,
            tonnes_per_year REAL,
            transport_total INTEGER,
            electricity_total INTEGER,
            diet_lifestyle_total INTEGER,
            trans_pct INTEGER,
            elec_pct INTEGER,
            diet_pct INTEGER,
            saved_date TEXT,
            session_id TEXT
        )
    ''')
    
    # Migration handling: Ensure existing databases get the session_id column safely
    try:
        cursor.execute("ALTER TABLE reports ADD COLUMN session_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

# Automatically assigns a unique tracking ID to any new visitor session
@app.before_request
def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/assessment')
def assessment():
    return render_template('assessment.html')

@app.route('/result', methods=['GET', 'POST'])
def result():
    if request.method == 'GET':
        report = session.get('report_data')

        if not report:
            return redirect(url_for('home'))
        
        eco_score = report['eco_score']
        score_grade = report['score_grade']

        if eco_score >= 80:
            score_color = "#1A3020"
        elif eco_score >= 60:
            score_color = "#556B58"
        elif eco_score >= 40:
            score_color = "#C47A46"
        else:
            score_color = "#C45A46"

        return render_template(
            'result.html',
            eco_score=eco_score,
            score_grade=score_grade,
            score_color=score_color,
            annual_emissions="{:,}".format(report['annual_emissions']),
            tonnes_per_year=report['tonnes_per_year'],
            monthly_average="{:,}".format(report['monthly_average']),
            transport_total="{:,}".format(report['transport_total']),
            electricity_total="{:,}".format(report['electricity_total']),
            diet_lifestyle_total="{:,}".format(report['diet_lifestyle_total']),
            trans_pct=report['trans_pct'],
            elec_pct=report['elec_pct'],
            diet_pct=report['diet_pct'],
            trans_bar_color="#1B4332",
            elec_bar_color="#556B58",
            diet_bar_color="#C45A46",
            report_data=report,
            recommendations=[],
            is_saved_report=False,
            saved_date=None,
            show_toast=session.pop('report_saved', False)
        )
    # Gather responses safely for all 9 questions
    q0 = request.form.get('question_0', 'Walk')
    q1 = request.form.get('question_1', '< 5 kWh')
    q2 = request.form.get('question_2', 'Vegan')
    q3 = request.form.get('question_3', '0 flights')
    q4 = request.form.get('question_4', 'Biomass / Solar')
    q5 = request.form.get('question_5', 'Almost Never')
    q6 = request.form.get('question_6', 'Very Little')
    q7 = request.form.get('question_7', 'Everything')
    q8 = request.form.get('question_8', 'Conscious Saving')

    # --- CATEGORY 1: TRANSPORT EMISSIONS (kg CO2e per year) ---
    transport_map = {
        "Petrol Car": 2400, "Diesel Car": 2100, "Bus": 600, 
        "Bike": 50, "Train": 200, "Walk": 0
    }
    flight_map = {
        "0 flights": 0, "1–2 flights": 500, "3–5 flights": 1500, "More than 5": 3000
    }
    transport_total = transport_map.get(q0, 0) + flight_map.get(q3, 0)

    # --- CATEGORY 2: ELECTRICITY & ENERGY EMISSIONS (kg CO2e per year) ---
    elec_map = {
        "< 5 kWh": 400, "5–10 kWh": 1100, "10–20 kWh": 2400, "> 20 kWh": 4200
    }
    heat_map = {
        "Natural Gas": 1800, "Electricity": 1200, "Heating Oil": 2600, "Biomass / Solar": 200
    }
    electricity_total = elec_map.get(q1, 0) + heat_map.get(q4, 0)

    # --- CATEGORY 3: DIET & LIFESTYLE EMISSIONS (kg CO2e per year) ---
    diet_map = {
        "Frequent Meat": 2500, "Balanced Diet": 1700, "Vegetarian": 1100, "Vegan": 600
    }
    goods_map = {
        "Very Often": 1200, "Moderate": 700, "Rarely": 300, "Almost Never": 50
    }
    waste_map = {
        "Above Average": 600, "Average": 400, "Below Average": 200, "Very Little": 50
    }
    recycle_map = {
        "Everything": -200, "Most Things": -100, "Occasionally": 0, "Do Not Sort": 100
    }
    water_map = {
        "High Usage": 150, "Moderate Usage": 50, "Conscious Saving": -50
    }
    
    diet_lifestyle_total = (
        diet_map.get(q2, 0) + 
        goods_map.get(q5, 0) + 
        waste_map.get(q6, 0) + 
        recycle_map.get(q7, 0) + 
        water_map.get(q8, 0)
    )
    if diet_lifestyle_total < 200: 
        diet_lifestyle_total = 200

    # --- CALCULATION TOTALS ---
    annual_emissions = transport_total + electricity_total + diet_lifestyle_total
    monthly_average = round(annual_emissions / 12)
    tonnes_per_year = round(annual_emissions / 1000, 2)

    # Percentages
    if annual_emissions > 0:
        trans_pct = round((transport_total / annual_emissions) * 100)
        elec_pct = round((electricity_total / annual_emissions) * 100)
        diet_pct = 100 - (trans_pct + elec_pct)
    else:
        trans_pct, elec_pct, diet_pct = 33, 33, 34

    # --- ECO SCORE (Aligned exactly to target 11 for high scenario) ---
    base_score = 100 - (annual_emissions / 120.78)
    eco_score = max(5, min(95, round(base_score)))

    # Determine colors for bars dynamically based on footprint size
    trans_bar_color = "#C45A46" if trans_pct > 25 else "#6E8268"
    elec_bar_color = "#C45A46" if elec_pct > 25 else "#6E8268"
    diet_bar_color = "#C45A46" if diet_pct > 25 else "#6E8268"

    recommendations = []

    if trans_pct >= 35:
        recommendations.append({
            "category": "TRANSPORT",
            "icon": "directions_car", 
            "impact": "high impact",
            "title": "Switch to Public Transit or Carpooling",
            "description": "Replacing frequent car trips with public transit can significantly reduce emissions."
        })

    if elec_pct >= 35:
        recommendations.append({
            "category": "ELECTRICITY",
            "icon": "bolt",
            "impact": "medium impact",
            "title": "Reduce Household Electricity Usage",
            "description": "Energy-efficient appliances and mindful consumption can lower your footprint."
        })

    if diet_pct >= 35:
        recommendations.append({
            "category": "DIET",
            "icon": "restaurant",
            "impact": "medium impact",
            "title": "Shift Toward Plant-Based Meals",
            "description": "Even reducing meat consumption a few times a week can have a measurable impact."
        })

    if len(recommendations) < 3:
        recommendations.extend([
            {
                "category": "GENERAL",
                "icon": "info",
                "impact": "low impact",
                "title": "Track Your Footprint Regularly",
                "description": "Small improvements over time create lasting environmental impact."
            },
            {
                "category": "LIFESTYLE",
                "icon": "droplet",
                "impact": "medium impact",
                "title": "Conserve Water and Energy",
                "description": "Simple habits like shorter showers and turning off unused appliances add up."
            }
        ])

    recommendations = recommendations[:5]    

    if eco_score >= 80:
        score_grade = "Excellent"
        score_color = "#1A3020"
    elif eco_score >= 60:
        score_grade = "Good"
        score_color = "#556B58"
    elif eco_score >= 40:
        score_grade = "Average"
        score_color = "#C47A46"
    else:
        score_grade = "Needs Improvement"
        score_color = "#C45A46"
    
    report_data = {
    "eco_score": eco_score,
    "score_grade": score_grade,
    "annual_emissions": annual_emissions,
    "monthly_average": monthly_average,
    "tonnes_per_year": tonnes_per_year,
    "transport_total": transport_total,
    "electricity_total": electricity_total,
    "diet_lifestyle_total": diet_lifestyle_total,
    "trans_pct": trans_pct,
    "elec_pct": elec_pct,
    "diet_pct": diet_pct
}
 
    session['report_data'] = report_data

    return render_template(
        'result.html',
        eco_score=eco_score,
        score_grade=score_grade,
        score_color=score_color,
        annual_emissions="{:,}".format(annual_emissions),
        tonnes_per_year=tonnes_per_year,
        monthly_average="{:,}".format(monthly_average),
        transport_total="{:,}".format(transport_total),
        electricity_total="{:,}".format(electricity_total),
        diet_lifestyle_total="{:,}".format(diet_lifestyle_total),
        trans_pct=trans_pct,
        elec_pct=elec_pct,
        diet_pct=diet_pct,
        trans_bar_color=trans_bar_color,
        elec_bar_color=elec_bar_color,
        diet_bar_color=diet_bar_color,
        report_data=report_data,
        recommendations=recommendations,
        is_saved_report=False,
        saved_date=None,
        show_toast=session.pop('report_saved', False)
    )

@app.route('/save_report', methods=['POST'])
def save_report():
    report = session.get('report_data')
    if not report:
        return redirect(url_for('home'))

    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Added session_id column and value to the INSERT statement
    cursor.execute('''
        INSERT INTO reports (
            eco_score,
            score_grade,
            annual_emissions,
            monthly_average,
            tonnes_per_year,
            transport_total,
            electricity_total,
            diet_lifestyle_total,
            trans_pct,
            elec_pct,
            diet_pct,
            saved_date,
            session_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        report['eco_score'],
        report['score_grade'],
        report['annual_emissions'],
        report['monthly_average'],
        report['tonnes_per_year'],
        report['transport_total'],
        report['electricity_total'],
        report['diet_lifestyle_total'],
        report['trans_pct'],
        report['elec_pct'],
        report['diet_pct'],
        datetime.now().strftime("%d %b %Y, %H:%M"),
        session.get('session_id')  # <-- Saves the unique browser identifier
    ))

    conn.commit()
    conn.close()

    session['report_saved'] = True
    return redirect(url_for('result'))


@app.route('/history')
def history():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Filter reports strictly by the visitor's session ID
    cursor.execute('''
        SELECT *
        FROM reports
        WHERE session_id = ?
        ORDER BY id DESC
    ''', (session.get('session_id'),))

    reports = cursor.fetchall()
    conn.close()

    return render_template('history.html', reports=reports)


@app.route('/report/<int:report_id>')
def view_report(report_id):
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM reports WHERE id = ?',
        (report_id,)
    )
    report = cursor.fetchone()
    conn.close()

    if report is None:
        return "Report not found", 404

    # Security check: Ensure current session ID matches the report's owner
    if report['session_id'] != session.get('session_id'):
        return "Access denied: Private report", 403

    return render_template(
        'result.html',
        eco_score=report['eco_score'],
        score_grade=report['score_grade'],
        score_color=(
            "#1A3020" if report['eco_score'] >= 80
            else "#556B58" if report['eco_score'] >= 60
            else "#C47A46" if report['eco_score'] >= 40
            else "#C45A46"
        ),
        annual_emissions="{:,}".format(report['annual_emissions']),
        monthly_average="{:,}".format(report['monthly_average']),
        tonnes_per_year=report['tonnes_per_year'],
        transport_total="{:,}".format(report['transport_total']),
        electricity_total="{:,}".format(report['electricity_total']),
        diet_lifestyle_total="{:,}".format(report['diet_lifestyle_total']),
        trans_pct=report['trans_pct'],
        elec_pct=report['elec_pct'],
        diet_pct=report['diet_pct'],
        trans_bar_color="#1B4332",
        elec_bar_color="#556B58",
        diet_bar_color="#C45A46",
        report_data=dict(report),
        is_saved_report=True,
        saved_date=report['saved_date'],
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
