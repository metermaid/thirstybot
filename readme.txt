THIRSTYBOT
"I'm thirsty!"

========

TO RUN: 
Have python.
"python app.py"

========
The Thirstybot  alcoholic drink recommendation system is a web application that uses data mining techniques to provide users with recommendations of new drinks.

Thirstybot was built in Python on top of the Flask web framework and Jinja templating engine, using a SQLite3 Database.

Users of the system can create an account, login and rate drinks.

User-Based recommendations - Manhattan Distance
- The nearest neighbouring user based on their previous recommendations are analysed to provide you with a list of possible drinks you may also like

Item-Based recommendations - Cosine Similarity
- Finds items that are most similar to items that the user has already rated by. 
- The most similar drinks are found by finding multiple users who have rated the drink the same. From those users, if they have all rated a different drink a similar rating, it can be said that those two drinks are similar.