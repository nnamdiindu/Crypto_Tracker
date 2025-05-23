import os
import requests
from datetime import timedelta
from datetime import datetime, timezone
from dateutil import parser
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


# Custom formatter
def format_number(num):
    try:
        num = float(num)
        if num >= 1_000_000_000_000:
            return f"{num/1_000_000_000_000:.1f}T"
        elif num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:.2f}"
    except:
        return num  # fallback for non-numeric input

# Register it as a Jinja filter
app.jinja_env.filters['compact'] = format_number


# Format Time Function
def time_ago(timestamp_str):
    try:
        timestamp = parser.isoparse(timestamp_str)
        now = datetime.now(timezone.utc)
        diff = now - timestamp

        seconds = diff.total_seconds()
        minutes = seconds / 60
        hours = minutes / 60
        days = hours / 24

        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif minutes < 60:
            return f"{int(minutes)} minutes ago"
        elif hours < 24:
            return f"{int(hours)} hours ago"
        else:
            return f"{int(days)} days ago"
    except Exception as e:
        return "Invalid date"

# Register the filter with Jinja
app.jinja_env.filters['timeago'] = time_ago


def get_bitcoin_chart_data(days=7):
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily' if days > 1 else 'hourly'
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Extract and format data
    labels = []
    prices = []

    for timestamp, price in data['prices']:
        dt = datetime.fromtimestamp(timestamp / 1000)

        # Format label based on time period
        if days == 1:
            label = dt.strftime('%H:%M')
        else:
            label = dt.strftime('%m/%d')

        labels.append(label)
        prices.append(round(price, 2))

    return {
        'labels': labels,
        'data': prices
    }


def get_top_cryptocurrencies():
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
    return crypto_data


def get_market_data():
    # Global Market Data API Call
    url = "https://api.coingecko.com/api/v3/global"

    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": os.environ.get("COINGECKO_API_KEY")
    }
    response = requests.get(url, headers=headers)
    market_data = response.json()
    return market_data


def get_market_news():
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

    return news_articles


@app.route("/", methods=["GET", "POST"])
def dashboard():

    crypto_data = get_top_cryptocurrencies()

    market_data = get_market_data()

    news_articles = get_market_news()

    chart_data = get_bitcoin_chart_data(days=30)

    return render_template("portfolio.html", crypto_data=crypto_data, market_data=market_data, news_articles=news_articles, chart_data=chart_data, current_user=current_user)


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
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)