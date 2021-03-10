from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

import requests
import json
import time

import os
from boto.s3.connection import S3Connection

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(30))
    phone_number = db.Column(db.String(20), nullable=False)
    min_temp = db.Column(db.Integer)
    max_temp = db.Column(db.Integer)
    zipcode = db.Column(db.Integer)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Schedule %r>' % self.id


def KToF(kelvin):
    return 9/5*(kelvin-273.15)+32


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        password = request.form['password']
        if str(password).upper() == "FRANCISCO":
            schedule_min_temp = request.form['min_temp']
            # print("min temp is " + schedule_min_temp)
            schedule_max_temp = request.form['max_temp']
            schedule_zipcode = request.form['zipcode']
            schedule_phone_number = request.form['phone_number']
            schedule_email = request.form['email']
            schedule_password = request.form['password']
            #new_schedule = Todo(min_temp=schedule_min_temp)
            # new_schedule = Todo(min_temp=schedule_min_temp, max_temp=schedule_max_temp, zipcode=schedule_zipcode,
            #                    phone_number=schedule_phone_number, email=schedule_email, date_created=datetime.utcnow)
            new_schedule = Todo(phone_number=schedule_phone_number,
                                min_temp=schedule_min_temp,
                                max_temp=schedule_max_temp,
                                zipcode=schedule_zipcode,
                                email=schedule_email)
            out = open_weather_request(
                schedule_min_temp, schedule_max_temp, schedule_zipcode)
            text_response = send_text(out, schedule_phone_number)
            out = text_response
            print(out)
            try:
                db.session.add(new_schedule)
                db.session.commit()

                # print(out)
                # return redirect('/')
                return render_template('index.html', out=out)
            except:
                return "There was an issue adding your schedule."
        else:
            return "Wrong password."
    else:
        schedules = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', schedules=schedules)


@app.route('/delete/<int:id>')
def delete(id):
    schedule_to_delete = Todo.query.get_or_404(id)
    try:
        db.session.delete(schedule_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return "There was a problem deleting that task"


def open_weather_request(min_temp: int, max_temp: int, zipcode):
    print("index loaded")
    # OPENWEATHER_AUTH = ''  # REMOVE BEFORE COMMITTING!!

    # OPENWEATHER_AUTH = S3Connection(
    #    os.environ['S3_KEY'], os.environ['OPENWEATHER_AUTH'])

    OPENWEATHER_AUTH = os.environ.get('OPENWEATHER_AUTH')

    url = "http://api.openweathermap.org/data/2.5/forecast?q=" + \
        zipcode+"&appid="+OPENWEATHER_AUTH

    payload = {}
    headers = {
        'appid': ''+OPENWEATHER_AUTH
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    data = json.loads(response.text)
    THREEHOURS = 60*60*3
    #min_temp = 70
    #max_temp = 80

    print("COD:"+data['cod'])
    print("Count:"+(str(data['cnt'])))
    count = data['cnt']

    days = []
    epoch_time = datetime.now()
    day = epoch_time.strftime("%a %m/%d")
    weather_times = {}
    # weather_times.setdefault(day, [])
    for three_hour_inc in range(count):
        epoch_time = data["list"][three_hour_inc]['dt']
        epoch_time = datetime.fromtimestamp(epoch_time)
        the_date = epoch_time.strftime("%a %m/%d")
        the_time = epoch_time.strftime("%-I:%M%p")

        temp = data["list"][three_hour_inc]["main"]["temp"]
        temp = round(KToF(temp), 2)

        if float(temp) <= float(max_temp) and float(temp) >= float(min_temp):
            if the_date not in days:
                days.append(the_date)
            if the_date not in weather_times:
                weather_times.update({the_date: []})
            weather_times[the_date].append(the_time)
            # days[the_date].append(the_time)

            # print("the time: " + str(the_time))
            # print("temp:" + str(temp))
    # print(days)
    # print(weather_times)

    out = "Days with temps["+str(min_temp)+"F-"+str(max_temp)+"F]%0a"
    for k in range(len(days)):
        if k > 0:
            out += "]%0a"
        day = days[k]
        out += day + "%0a["
        if len(weather_times[day]) > 0:
            for i in range(len(weather_times[day])):
                out += weather_times[day][i]
                if i < len(weather_times[day])-1:
                    out += ","
        if k == len(days)-1:
            out += "]"
    return out


def send_text(message: str, destination_number: str):
    TWILIO_AUTH = os.environ.get('TWILIO_AUTH')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    TWILIO_SID = os.environ.get('TWILIO_SID')
    url = "https://api.twilio.com/2010-04-01/Accounts/"+TWILIO_SID+"/Messages.json"

    payload = 'To=%2B1' + destination_number + '&Body=' + message + \
        '&MediaUrl=https%3A%2F%2Fmedia.giphy.com%2Fmedia%2FPnUatAYWMEMvmiwsyx%2Fgiphy.gif&From=9165072052'
    headers = {
        'Authorization': 'Basic '+TWILIO_AUTH,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return response.text


if __name__ == "__main__":
    app.run(debug=True)
