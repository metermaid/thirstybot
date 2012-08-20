# -*- coding: utf-8 -*-
"""
    ThirstyBot
    ~~~~~~~~

    I'M SO THIRSTY.

"""
from __future__ import with_statement
import time
from sqlite3 import dbapi2 as sqlite3

from hashlib import md5
from datetime import datetime
from contextlib import closing
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash
from werkzeug import check_password_hash, generate_password_hash
from math import sqrt


# flask-peewee bindings
from flask_peewee.db import Database
from flask_peewee.auth import Auth

from peewee import *

# configure our database
DATABASE = {
    'name': 'thirsty.db',
    'engine': 'peewee.SqliteDatabase',
}
PER_PAGE = 30
DATABASE2 = 'thirsty.db'

# configuration
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('THIRSTYBOT_SETTINGS', silent=True)

# instantiate the db wrapper
db = Database(app)


#new stuff
frequencies = {}
deviations = {}

# create an Auth object for use with our flask app and database wrapper
auth = Auth(app, db)

class Drink(db.Model):
    name = CharField(unique = True)
    photoURL = CharField()
    description = TextField() 
    
class Rating(db.Model):
    user_id = ForeignKeyField(auth.User)
    drink_id = ForeignKeyField(Drink)
    rating = IntegerField()


def manhattan(rating1, rating2):
    """Computes the Manhattan distance. Both rating1 and rating2 are dictionaries
       of the form {'The Strokes': 3.0, 'Slightly Stoopid': 2.5}"""
    distance = 0
    total = 0
    for key in rating1:
        if key in rating2:
            distance += abs(rating1[key] - rating2[key])
            total += 1
    if total > 0:
        return distance / total
    else:
        return -1 #Indicates no ratings in common

                
def formatDrinkDict(list):
    newDict = {}
    for item in list:
        newDict[item.user_id] = item.rating
    return newDict

def formatUserDict(list):
    newDict = {}
    for item in list:
        newDict[item.drink_id] = item.rating
    return newDict
        
def computeNearestNeighbor(userID):
    """creates a sorted list of items based on their distance to givenItem"""
    user = auth.User.filter(id = userID)
    user = user.get()
    userRatings = Rating.filter(user_id = user)
    userRatings = formatUserDict(userRatings)
    
    userList = auth.User.select()

    distances = []
    for item in userList:
        if item.id == userID:
          continue
        currentRatings = Ratings.filter(user_id = item)
        currentRatings = formatUserDict(currentRatings)

        distance = manhattan(userRatings, currentRatings)
        distances.append((distance, item))
    # sort based on distance -- closest first
    distances.sort()
    return distances

def recommendBasedOnUsers(userID):
    """Give list of recommendations"""
    # first find nearest neighbor
        
    nearest = computeNearestNeighbor(userID)[0][1]
    nearest = auth.User.filter(id = nearest)
    nearest = nearest.get()
    recommendations = []
    # now find bands neighbor rated that user didn't
    
    neighborRatings = Ratings.filter(user_id = nearest)
    user = auth.User.filter(id = userID)
    user = user.get()
    userRatings = Ratings.filter(user_id = user)

    for rating in neighborRatings:
        flag = false
        for rating2 in userRatings:
            if rating.id == rating2.id:
              flag = true
        if flag == false:
          recommendations.append(rating.id)
    # using the fn sorted for variety - sort is more efficient
    return recommendations

def recommendBasedOnDrink(drinkID):
    """creates a sorted list of items based on their distance to givenItem"""
    drink = Drink.filter(id = drinkID)
    drink = drink.get()
    drinkRatings = formatDrinkDict(Ratings.filter(drink_id = drink))

    
    list = drink.select()

    distances = []
    for item in list:
        if item.id == drinkID:
          continue
        currentRatings = formatDrinkDict(Ratings.filter(drink_id = item))
        distance = manhattan(drinkRatings, currentRatings)
        distances.append((distance, item))
    # sort based on distance -- closest first
    distances.sort()
    return distances[0:2]
    
def computeDeviations():
	#for each person in the data:
	#    get their ratings
  list = auth.User.select()
  
  distances = []
  for item in list:
    user = auth.User.filter(id=item.id)
    user = user.get()
    userRatings = formatUserDict(Ratings.filter(user_id = user))

    for (item, rating) in ratings.items():
        frequencies.setdefault(item, {})
        deviations.setdefault(item, {})
        #for each item2 & rating2 in that set of ratings:
        for (item2, rating2) in ratings.items():
            if item != item2:
                #add the difference between the ratings to our computation
                frequencies[item].setdefault(item2, 0)
                deviations[item].setdefault(item2, 0.0)
                frequencies[item][item2] += 1
                deviations[item][item2] += rating - rating2
	
	for (item, ratings) in deviations.items():
	    for item2 in ratings:
	        ratings[item2] /= frequencies[item][item2]   

    
def recommendBasedOnItemSet(userID):
  recommendations = {}
  frequencies1 = {}
  user = auth.User.filter(id=userID)
  user = user.get()
  userRatings = formatUserDict(Ratings.filter(user_id = user))

  computeDeviations()

  # for every item and rating in the user's recommendations
  for (userItem, userRating) in userRatings.items():
      #for every item in our dataset that the user didn't rate
      for (diffItem, diffRatings) in deviations.items():
        if(diffItem not in userRatings and userItem in deviations[diffItem]):
          freq = frequencies[diffItem][userItem]
          recommendations.setdefault(diffItem, 0.0)
          frequencies1.setdefault(diffItem, 0)
          # add to the running sum representing the numerator of the formula
          recommendations[diffItem] += (diffRatings[userItem] + userRating) * freq
          # keep a running sum of the frequency of diffitem
          frequencies1[diffItem] += freq
  recommendations =  [(k, v / frequencies1[k]) for (k, v) in recommendations.items()]
  # finally sort and return
  recommendations.sort(key=lambda artistTuple: artistTuple[1], reverse = True)
  recommendations =  [k for (k, v) in recommendations]	 

  return recommendations

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')

@app.route('/')
def recommendations():
    """Shows a users recommendations or if no user is logged in it will
    redirect to the public recommendations.  This recommendations shows the user's
    recommendations as well as all the recommendations of followed users.
    """
    user = auth.get_logged_in_user()
    if not user:
        return redirect(url_for('public_recommendations'))
    recAlg = recommendBasedOnUsers(user.id)
    recAlg2 = recommendBasedOnItemSet(user.id)
    recs = []
    recs2 = []
    
    for recommendation in recAlg:
        query = Drinks.filter(id=recommendation['drink_id'])
        recs.extend(query)
    for recommendation in recAlg2:
       query = Drinks.filter(id=recommendation['drink_id'])
       recs2.extend(query)
    return render_template('recommendations.html', recommendations=recs, recommendations2=recs2)


@app.route('/public')
def public_recommendations():
    """Displays a random selection of highly rated drinks."""
    recs = Drink.select({
      Drink:['*'],
      Rating:[Sum('rating'),Count('rating')],
    }).group_by(Drink).join(Rating)
    return render_template('recommendations.html', recommendations=recs)

@app.route('/all')
def all_drinks():
    """Displays a random selection of highly rated drinks."""
    recs = Drink.select()
    return render_template('recommendations.html', recommendations=recs)

@app.route('/user/<username>')
def user_recommendations(username):
    """Displays recommendations for a user."""
    profile_user = auth.User(username=username)
    profile_user = profile_user.get()
    if profile_user is None:
        abort(404)
    recs = recommendBasedOnUsers(profile_user.id)
    return render_template('recommendations.html', recommendations=recs,
            profile_user=profile_user)
            
@app.route('/drink/<drink_id>')
def display_drink(drink_id):
    drink = Drink.filter(id=drink_id)
    drink = drink.get()
    recs = recommendBasedOnDrink(drink_id)                      
    if drink is None:
        abort(404)
    return render_template('drink.html', drink=drink, recommendations=recs)


@app.route('/drink/<drink_id>/rate/<rating>')
@auth.login_required
def rate(drink_id, rating):
    """ Rate the given drink for the user """
    drink_id = Drink.filter(id = drink_id)
    rating = Rating.create(
      user_id = auth.get_logged_in_user(),
      drink_id = drink_id.get(),
      rating = rating,
    )
    flash('Rating has been successfully made!')
    return redirect(url_for('recommendations'))

@app.route('/add_drink', methods=['GET', 'POST'])
def add_drink():
    error = None
    if request.method == 'POST' and request.form['name']:
        if not request.form['name']:
            error = 'You have to enter a name'
        elif not request.form['description']:
            error = 'You have to enter a description'
        elif not request.form['photoURL']:
            error = 'You have to enter a photo URL'
        else:
            drink = Drink.create(
              name = request.form['name'],
              description = request.form['description'],
              photoURL = request.form['photoURL'],
            )
            flash('You added a drink you alcoholic!!!!')
            return redirect(url_for('recommendations'))
    return render_template('add_drink.html', error=error)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST' and request.form['username']:
        try:
            user = auth.User.get(username=request.form['username'])
            flash('That username is already taken')
        except auth.User.DoesNotExist:
            if request.form['password'] != request.form['password2']:
              error = 'The two passwords do not match'
            user = auth.User(
                username=request.form['username'],
                email=request.form['email'],
                join_date=datetime.now()
            )
            user.set_password(request.form['password'])
            user.save()
            
            auth.login_user(user)
            return redirect(url_for('recommendations'))

    return render_template('register.html', error=error)
    
# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime


if __name__ == '__main__':
    auth.User.create_table(fail_silently=True)
    Rating.create_table(fail_silently=True)
    Drink.create_table(fail_silently=True)
    app.run()
