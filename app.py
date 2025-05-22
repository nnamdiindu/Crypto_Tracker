import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash
from flask_login import UserMixin, current_user, login_user, logout_user, login_required, LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm

load_dotenv()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")
app.secret_key = os.environ.get("SECRET_KEY")
bootstrap = Bootstrap5(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
db.init_app(app)


class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(120), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home():


    return render_template("index.html", current_user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            flash("You've already signed up, please login.")
            return redirect(url_for("login"))

        hashed_and_salted_password = generate_password_hash(
            password=password,
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            name = form.name.data,
            email = form.email.data,
            password = hashed_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("dashboard"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("dashboard"))

            else:
                flash("Incorrect password, please try again.")
                return redirect(url_for("login"))
        else:
            flash("Email doesn't exist, please sign up.")
            return redirect(url_for("register"))

    return render_template("login.html", form=form, current_user=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    # Top 10 Coins API Call
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params)
    crypto_data = response.json()


    # Global Market Data API Call
    url = "https://api.coingecko.com/api/v3/global"
    headers = {"accept": "application/json","x-cg-demo-api-key": os.environ.get("COINGECKO_API_KEY")}
    response = requests.get(url, headers=headers)
    market_data = response.json()

    # Crypto News API Call
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=7)

    params = {
        "q": 'cryptocurrency OR bitcoin OR ethereum OR "crypto market"',
        "from": start_date,
        "to": end_date,
        "sortBy": "popularity",
        "language": "en",
        "pageSize": 10,  # Max articles per request
        "apiKey": os.environ.get("NEWS_API_KEY")
    }

    response = requests.get('https://newsapi.org/v2/everything', params=params)
    news_articles = response.json()["articles"]


    return render_template("portfolio.html", crypto_data=crypto_data, market_data=market_data, news_articles=news_articles, current_user=current_user)



if __name__ == "__main__":
    app.run(debug=True)