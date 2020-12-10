from flask import Flask, render_template, url_for, request
import os
import numpy as np
import pandas as pd
import pickle
from Similarity import find_similar, get_closest
import re

image_folder = os.path.join('static', 'images')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = image_folder

@app.route('/', methods=['GET', 'POST'])
def home():

    background = os.path.join(app.config['UPLOAD_FOLDER'], 'Earth.png')
    return render_template("Test.html", background_image=background)

@app.route('/closest', methods=['POST', 'GET'])
def show_closest():
    
    background = os.path.join(app.config['UPLOAD_FOLDER'], 'Earth.png')
    cosine_pickle = os.path.join(app.config['UPLOAD_FOLDER'], 'cosine_sims.pickle')
    foods_pickle = os.path.join(app.config['UPLOAD_FOLDER'], 'initial_df.pickle')

    if request.method == 'POST':
        selection = request.form['food-search']
        with open(cosine_pickle, "rb") as to_read:
            cosines = pickle.load(to_read)
        with open(foods_pickle, "rb") as to_read:
            df = pickle.load(to_read)
        closest, text, origin, image_link, page_link = get_closest(selection, cosines, df)


        return render_template("Test-test.html", background_image=background, closest=closest, origin=origin, text=text, image_link=image_link, page_link=page_link, selection=selection)

@app.route('/closest2', methods=['POST', 'GET'])
def show_country():

    background = os.path.join(app.config['UPLOAD_FOLDER'], 'Earth.png')
    cosine_pickle = os.path.join(app.config['UPLOAD_FOLDER'], 'cosine_sims.pickle')
    foods_pickle = os.path.join(app.config['UPLOAD_FOLDER'], 'initial_df.pickle')

    if request.method == 'POST':
        selection = request.form['food-search']
        with open(cosine_pickle, "rb") as to_read:
            cosines = pickle.load(to_read)
        with open(foods_pickle, "rb") as to_read:
            df = pickle.load(to_read)
        closest, text, origin, image_link, page_link = get_closest(selection, cosines, df)


        return render_template("Test-test-test.html", background_image=background, closest=closest, origin=origin, text=text, image_link=image_link, page_link=page_link)


@app.route('/predict', methods=['POST', 'GET'])
def predict():
    
    court = os.path.join(app.config['UPLOAD_FOLDER'], 'Court 1 smaller.png')
    player_circle = os.path.join(app.config['UPLOAD_FOLDER'], 'Circle.png')

    updated_df = os.path.join(app.config['UPLOAD_FOLDER'], 'updated_df.pickle')
    model = os.path.join(app.config['UPLOAD_FOLDER'], 'model.pickle')
    ss = os.path.join(app.config['UPLOAD_FOLDER'], 'scaler.pickle')

    if request.method == 'POST':
        parameters = request.form['team-form']
        year_choice = parameters.split(", ")[2]
        max_age = parameters.split(", ")[1]
        if max_age == "all":
            max_age = 50
        teams = parameters.split(", ")[0]

        df = pickle.load(open(updated_df, "rb"))
        MODEL = pickle.load(open(model, "rb"))
        scaler = pickle.load(open(ss, "rb"))

        top_24 = final_model(MODEL, scaler, df, int(f'20{year_choice[-2:]}'), \
            max_age=int(max_age), teams=teams, first_timers_only=False)

        return render_template("nba_results.html", user_image=court, circle=player_circle, all_stars=top_24)

if __name__ == '__main__':
    app.run(debug=True)

