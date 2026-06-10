from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    result = ""
    recommendation = ""
    
    if request.method == 'POST':
        distance = request.form['distance']
        transport = request.form['transport']

        distance = float(distance)

        if transport == "Car":
            footprint = distance * 0.21
            recommendation = "Try carpooling or using public transport a few days a week to reduce emissions."
        elif transport == "Bus":
            footprint = distance * 0.10
            recommendation = "Great choice! Public transport produces fewer emissions per person than most cars."
        elif transport == "Bike":
            footprint = distance * 0.05
            recommendation = "Biking is an eco-friendly option. Keep it up to reduce your carbon footprint!"
        elif transport == "Train":
            footprint = distance * 0.04
            recommendation = "Trains are one of the most efficient transport options. Nice choice!"
        else:
            footprint = 0
            recommendation = "Excellent! Walking produces virtually no transport-related carbon emissions."

        result = f"Estimated Carbon Footprint: {footprint:.2f} kg CO₂ per day"

    return render_template('index.html', result=result , recommendation=recommendation)

if __name__ == '__main__':
    app.run(debug=True)