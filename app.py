from flask import Flask, render_template, url_for, request, redirect, flash
from datetime import datetime
from werkzeug.utils import redirect
import pandas as pd
from get_my_books import BookData

app = Flask(__name__)
app.static_folder = 'static/css' 
app.secret_key = "poppadontpreach"
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/', methods=['POST', 'GET'])
def index():
    return render_template('index.html')

@app.route('/wrapped', methods=['POST', 'GET'])
def greeter():
    goodreads_user_id = request.form.get('goodreads_user_id')
    if goodreads_user_id == None:
        goodreads_user_id = '59826157'
    print('GOODREADS USER ID: ', goodreads_user_id)
    bd = BookData(goodreads_user_id)
    bd.df = bd.df.sort_values(by=['my_rating','book_title'], ascending=[False,True])
    # print(bd.df)
    top_5_books = bd.get_top_5_books(strip=True)
    top_5_genres = bd.get_most_read_genres()
    books_read = bd.get_number_of_books_read()
    pages_read = bd.get_pages_tured()
    covers = bd.df.cover.tolist()
    content = {
        'goodreads_user_id':goodreads_user_id,
        'top_5_books':top_5_books,
        'top_5_genres':top_5_genres,
        'books_read':books_read,
        'pages_read':pages_read,
        'covers':covers
    }

    return render_template("wrapped.html", **content)


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
