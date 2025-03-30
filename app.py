from flask import Flask, request, render_template, redirect, session, url_for, flash
import pickle
import numpy as np
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Initialize Flask app
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Soham@1549' 


# Initialize database and Bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Load the trained model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

# Prediction Model (Stores Predictions)
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    children = db.Column(db.Integer, nullable=False)
    smoker = db.Column(db.Boolean, nullable=False)
    region = db.Column(db.String(50), nullable=False)
    predicted_cost = db.Column(db.Float, nullable=False)

    def __init__(self, user_id, age, bmi, children, smoker, region, predicted_cost):
        self.user_id = user_id
        self.age = age
        self.bmi = bmi
        self.children = children
        self.smoker = smoker
        self.region = region
        self.predicted_cost = predicted_cost

# Ensure database is created
with app.app_context():
    db.create_all()

# Home Route
@app.route("/")
def home():
    return render_template("index.html")

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User already exists! Try logging in.", "danger")
            return redirect(url_for("register"))

        # Create new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Find user
        user = User.query.filter_by(email=email).first()

        # Authenticate
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")

# Dashboard Route (Now Shows Past Predictions)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))
    
    # Fetch past predictions for logged-in user
    user_predictions = Prediction.query.filter_by(user_id=session["user_id"]).all()
    
    return render_template("dashboard.html", username=session["username"], predictions=user_predictions)

# Prediction Route (Now Saves to Database)
@app.route("/predict", methods=["POST"])
def predict():
    if "user_id" not in session:
        flash("Please log in to access predictions!", "warning")
        return redirect(url_for("login"))

    try:
        # Get input values
        age = int(request.form["age"])
        bmi = float(request.form["bmi"])
        children = int(request.form["children"])
        smoker = 1 if request.form["smoker"] == "yes" else 0
        region = request.form["region"]

        # One-hot encoding for region
        region_features = {"region_northeast": 0, "region_northwest": 0, "region_southeast": 0, "region_southwest": 0}
        if f"region_{region}" in region_features:
            region_features[f"region_{region}"] = 1  

        # Prepare input array
        features = [age, bmi, children, smoker] + list(region_features.values())
        features = np.array(features).reshape(1, -1)

        # Make prediction
        prediction = model.predict(features)[0]

        # Save prediction in database
        new_prediction = Prediction(user_id=session["user_id"], age=age, bmi=bmi, children=children, 
                                    smoker=smoker, region=region, predicted_cost=prediction)
        db.session.add(new_prediction)
        db.session.commit()

        return render_template("result.html", prediction=round(prediction, 2))

    except Exception as e:
        return render_template("result.html", prediction=f"Error: {str(e)}")

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True, port=5000)
