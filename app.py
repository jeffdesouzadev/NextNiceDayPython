from flask import Flask, render_template, url_for, request, redirect
from datetime import datetime

import requests
import re
import json
import time


import os
from boto.s3.connection import S3Connection

app = Flask(__name__)


def KToF(kelvin):
    return 9/5*(kelvin-273.15)+32


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        password = request.form['password']
        if str(password).upper() == "FRANCISCO":
            min_temp = request.form['min_temp']
            max_temp = request.form['max_temp']
            zipcode = request.form['zipcode']
            phone_number = request.form['phone_number']
            phone_number = re.sub('\D', '', phone_number)
            password = request.form['password']

            data = request_openweather_five_day(zipcode)
            text_message = filter_for_nice_days(
                min_temp, max_temp, zipcode, data)
            texting_response = send_text(text_message, phone_number)

            return render_template('submitted.html', min_temp=min_temp, max_temp=max_temp, zipcode=zipcode, phone_number=phone_number)
        else:
            return "Wrong password."
    else:
        return render_template('index.html')


def request_openweather_five_day(zipcode):
    print("index loaded")

    OPENWEATHER_AUTH = os.environ.get('OPENWEATHER_AUTH')
    if(OPENWEATHER_AUTH is None):
        print("OPENWEATHER auth missing")

    url = "http://api.openweathermap.org/data/2.5/forecast?q=" + \
        zipcode+"&appid="+OPENWEATHER_AUTH

    payload = {}
    headers = {
        'appid': ''+OPENWEATHER_AUTH
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    data = json.loads(response.text)
    return data


def filter_for_nice_days(min_temp: int, max_temp: int, zipcode, data):
    print("COD:"+data['cod'])
    print("Count:"+(str(data['cnt'])))
    count = data['cnt']

    days = []
    epoch_time = datetime.now()
    day = epoch_time.strftime("%a %m/%d")
    weather_times = {}

    for three_hour_inc in range(count):
        epoch_time = data["list"][three_hour_inc]['dt']
        epoch_time = datetime.fromtimestamp(epoch_time)
        the_date = epoch_time.strftime("%a %m/%d")
        the_time = epoch_time.strftime("%-I%p")

        temp = data["list"][three_hour_inc]["main"]["temp"]
        temp = round(KToF(temp), 2)

        if float(temp) <= float(max_temp) and float(temp) >= float(min_temp):
            if the_date not in days:
                days.append(the_date)
            if the_date not in weather_times:
                weather_times.update({the_date: []})
            weather_times[the_date].append(the_time)

    out = "Days with temps["+str(min_temp)+"F-"+str(max_temp)+"F]%0a"
    if len(days) < 1:
        out += "<None found!>"
    else:
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

    if(TWILIO_AUTH is None or TWILIO_PHONE_NUMBER is None or TWILIO_SID is None):
        print("Twilio auth missing")
    else:
        print("Twilio auth is there")
    url = "https://api.twilio.com/2010-04-01/Accounts/"+TWILIO_SID+"/Messages.json"

    payload = 'To=%2B1' + destination_number + '&Body=' + message + \
        '&MediaUrl=https%3A%2F%2Fmedia.giphy.com%2Fmedia%2FPnUatAYWMEMvmiwsyx%2Fgiphy.gif&From=9165072052'
    headers = {
        'Authorization': 'Basic '+TWILIO_AUTH,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.text)
    except Exception as ex:
        print("something went wrong with twilio? "+str(ex))

    return response.text


if __name__ == "__main__":
    app.run(debug=True)
