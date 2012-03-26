# -*- coding: utf-8 -*-
"""
    ThirstyBot
    ~~~~~~~~

    I'M SO THIRSTY.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
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


# configuration
DATABASE = 'thirsty.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('THIRSTYBOT_SETTINGS', silent=True)

#new styffsd
frequencies = {}
deviations = {}

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
        newDict[item['user_id']] = item['rating']
    return newDict

def formatUserDict(list):
    newDict = {}
    for item in list:
        newDict[item['drink_id']] = item['rating']
    return newDict
        
def computeNearestNeighbor(userID):
    """creates a sorted list of items based on their distance to givenItem"""
    
    userRatings = query_db('select drink_id, rating from ratings where user_id = ?', [userID])
    userRatings = formatUserDict(userRatings)
    
    list = query_db('select user_id from users where user_id != ?', [userID])

    distances = []
    for item in list:
        currentRatings = query_db('select drink_id, rating from ratings where user_id = ?', [item['user_id']])
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

    recommendations = []
    # now find bands neighbor rated that user didn't
    neighborRatings = query_db('select drink_id from ratings where user_id = ?', [nearest['user_id']])
    userRatings = query_db('select drink_id from ratings where user_id = ?', [userID])

    for drink in neighborRatings:
        if not drink in userRatings:
            recommendations.append(drink)
    # using the fn sorted for variety - sort is more efficient
    return recommendations

def recommendBasedOnDrink(drinkID):
    """creates a sorted list of items based on their distance to givenItem"""
    
    drinkRatings = query_db('select user_id, rating from ratings where drink_id = ?', [drinkID])
    drinkRatings = formatDrinkDict(drinkRatings)
    list = query_db('select * from drinks where drink_id != ?', [drinkID])

    distances = []
    for item in list:
        currentRatings = query_db('select user_id, rating from ratings where drink_id = ?', [item['drink_id']])
        currentRatings = formatDrinkDict(currentRatings)
        distance = manhattan(drinkRatings, currentRatings)
        distances.append((distance, item))
    # sort based on distance -- closest first
    distances.sort()
    return distances[0:2]
    
def computeDeviations():
	#for each person in the data:
	#    get their ratings
  list = query_db('select user_id from users')
  
  distances = []
  for item in list:
    ratings = formatUserDict(query_db('select drink_id, rating from ratings where user_id = ?', [item['user_id']]))
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
	userRatings = formatUserDict(query_db('select drink_id, rating from ratings where user_id = ?', [userID]))
	
	computeDeviations()
	
	print "When you knock on my door"   
	# for every item and rating in the user's recommendations
	for (userItem, userRating) in userRatings.items():
	    #for every item in our dataset that the user didn't rate
	    print "LOL"
	    for (diffItem, diffRatings) in deviations.items():
	    	if(diffItem not in userRatings and userItem in deviations[diffItem]):
				freq = frequencies[diffItem][userItem]
				recommendations.setdefault(diffItem, 0.0)
				frequencies1.setdefault(diffItem, 0)
				# add to the running sum representing the numerator of the formula
				recommendations[diffItem] += (diffRatings[userItem] + userRating) * freq
				# keep a running sum of the frequency of diffitem
				frequencies1[diffItem] += freq
	print "We'll be waiting for you"  
	recommendations =  [(k, v / frequencies1[k]) for (k, v) in recommendations.items()]
	# finally sort and return
	recommendations.sort(key=lambda artistTuple: artistTuple[1], reverse = True)
	recommendations =  [k for (k, v) in recommendations]	 
	
	return recommendations

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv


def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = g.db.execute('select user_id from users where username = ?',
                       [username]).fetchone()
    return rv[0] if rv else None


def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d @ %H:%M')


def gravatar_url(email, size=80):
    """Return the gravatar image for the given email address."""
    return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
        (md5(email.strip().lower().encode('utf-8')).hexdigest(), size)


@app.before_request
def before_request():
    """Make sure we are connected to the database each request and look
    up the current user so that we know he's there.
    """
    g.db = connect_db()
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from users where user_id = ?',
                          [session['user_id']], one=True)


@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def recommendations():
    """Shows a users recommendations or if no user is logged in it will
    redirect to the public recommendations.  This recommendations shows the user's
    recommendations as well as all the recommendations of followed users.
    """
    if not g.user:
        return redirect(url_for('public_recommendations'))
    recAlg = recommendBasedOnUsers(session['user_id'])
    recAlg2 = recommendBasedOnItemSet(session['user_id'])
    recs = []
    recs2 = []
    
    for recommendation in recAlg:
        recs.extend(query_db('select name, description, drink_id from drinks where drink_id = ?', [recommendation['drink_id']]))
    for recommendation in recAlg2:
        recs2.extend(query_db('select name, description, drink_id from drinks where drink_id = ?', [recommendation]))
    return render_template('recommendations.html', recommendations=recs, recommendations2=recs2)


@app.route('/public')
def public_recommendations():
    """Displays a random selection of highly rated drinks."""
    recs = query_db('select name, description, avg(rating), drink_id from ratings natural join drinks group by rating order by rating desc')
    return render_template('recommendations.html', recommendations=recs)

@app.route('/all')
def all_drinks():
    """Displays a random selection of highly rated drinks."""
    recs = query_db('select name, description, drink_id from drinks')
    return render_template('recommendations.html', recommendations=recs)

@app.route('/user/<username>')
def user_recommendations(username):
    """Displays recommendations for a user."""
    profile_user = query_db('select * from users where username = ?',
                            [username], one=True)
    if profile_user is None:
        abort(404)
    recs = recommendBasedOnUsers(profile_user.user_id)
    return render_template('recommendations.html', recommendations=recs,
            profile_user=profile_user)
            
@app.route('/drink/<drink_id>')
def display_drink(drink_id):
    drink = query_db('select * from drinks where drink_id = ?',
                            [drink_id], one=True)
    recs = recommendBasedOnDrink(drink_id)                      
    if drink is None:
        abort(404)
    return render_template('drink.html', drink=drink, recommendations=recs)


@app.route('/drink/<drink_id>/rate/<rating>')
def rate(drink_id, rating):
    """ Rate the given drink for the user """
    if not g.user:
        abort(401)
    if drink_id is None:
        abort(404)
    g.db.execute('insert into ratings (user_id, drink_id, rating) values (?, ?, ?)',
                [session['user_id'], drink_id, rating])
    g.db.commit()
    flash('Rating has been successfully made!')
    return redirect(url_for('recommendations'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('recommendations'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from users where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('recommendations'))
    return render_template('login.html', error=error)


@app.route('/add_drink', methods=['GET', 'POST'])
def add_drink():
    error = None
    if request.method == 'POST':
        if not request.form['name']:
            error = 'You have to enter a name'
        elif not request.form['description']:
            error = 'You have to enter a description'
        else:
            g.db.execute('''insert into drinks (
                name, description) values (?, ?)''',
                [request.form['name'], request.form['description']])
            g.db.commit()
            flash('You added a drink you alcoholic!!!!')
            return redirect(url_for('recommendations'))
    return render_template('add_drink.html', error=error)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('recommendations'))
    error = None
    if request.method == 'POST':
        if not request.form['username']:
            error = 'You have to enter a username'
        elif not request.form['email'] or \
                 '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif request.form['password'] != request.form['password2']:
            error = 'The two passwords do not match'
        elif get_user_id(request.form['username']) is not None:
            error = 'The username is already taken'
        else:
            g.db.execute('''insert into users (
                username, email, pw_hash) values (?, ?, ?)''',
                [request.form['username'], request.form['email'],
                 generate_password_hash(request.form['password'])])
            g.db.commit()
            flash('You were successfully registered and can login now')
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('public_recommendations'))


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['gravatar'] = gravatar_url


if __name__ == '__main__':
    app.run()
