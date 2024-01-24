from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flex_data = db.Column(db.Float, nullable=False)
    magnetometer_data = db.Column(db.Float, nullable=False)

@app.route('/receive_data', methods=['POST'])
def receive_data():
    try:
        received_data = request.get_json()

        flex_data = received_data.get('flex_data')
        magnetometer_data = received_data.get('magnetometer_data')

        new_data = SensorData(flex_data=flex_data, magnetometer_data=magnetometer_data)
        db.session.add(new_data)
        db.session.commit()

        return 'Data received and stored successfully', 200
    except Exception as e:
        print("Error processing data:", str(e))
        return 'Error processing data', 500

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=5000)
