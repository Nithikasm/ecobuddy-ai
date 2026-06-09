from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    result = ""

    if request.method == 'POST':
        distance = request.form['distance']
        transport = request.form['transport']

        distance = float(distance)

        if transport == "Car":
            footprint = distance * 0.21
        elif transport == "Bus":
            footprint = distance * 0.10
        elif transport == "Bike":
            footprint = distance * 0.05
        elif transport == "Train":
            footprint = distance * 0.04
        else:
            footprint = 0

        result = f"Estimated Carbon Footprint: {footprint:.2f} kg CO₂ per day"

    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)