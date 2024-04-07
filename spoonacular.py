from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import pymysql
import re
import pdfkit
import requests
import json
import os
import datetime
import urllib.parse
from fileinput import filename

app = Flask(__name__)
app.secret_key = 'tuesmignonne'

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

connection = pymysql.connect(host = 'localhost', 
    user = 'root',
    password = 'JKHKJEFFmysql115', 
    db = '303com_user', 
    local_infile = 1,
    cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

API_KEY = "b101d7eac19f452bad028f746b2dc9c7"
URL = f'https://api.spoonacular.com/recipes/complexSearch?'
# https://api.spoonacular.com/recipes/complexSearch?apiKey=b101d7eac19f452bad028f746b2dc9c7&number=5&instructionsRequired=True&addRecipeInformation=True&fillIngredients=True&includeIngredients=apple

hits_data = None

@app.route('/signIn', methods =['GET', 'POST'])
def signIn():
    msg = ''
    if request.method == 'POST' and 'Email' in request.form and 'PW' in request.form:
        Email = request.form['Email']
        PW = request.form['PW']
        connection.ping()
        cursor.execute('SELECT * FROM tbl_customer WHERE Email = % s AND Password = % s', (Email, PW))
        connection.commit()
        results = cursor.fetchone()
        if results:
            session['CustomerName'] = results['CustomerName']
            session['UserID'] = results['UserID']
            id = int(session['UserID'])
            # return redirect(url_for('inventory', id = id))
            return redirect(url_for('recipe'))
        else:
            msg = 'Incorrect username / password !'
    return render_template('recSignIn.html', msg = msg)

@app.route('/signUp', methods =['GET', 'POST'])
def signUp():
    msg = ''
    if request.method == 'POST' and 'Name' in request.form and 'Email' in request.form and 'PW' in request.form and 'ConfirmPW' in request.form and 'PhoneNumber' in request.form:
        Name = request.form['Name']
        PhoneNumber = request.form['PhoneNumber']
        Email = request.form['Email']
        PW = request.form['PW']
        ConfirmPW = request.form['ConfirmPW']

        connection.ping()
        cursor.execute('SELECT * FROM tbl_customer WHERE Email = % s', (Email))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', Email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', Name):
            msg = 'Name must contain only characters and numbers !'
        elif not Name or not Email or not PW:
            msg = 'Please fill out the form !'
        elif request.form['ConfirmPW'] != request.form['PW']:
            msg = 'Confirm Password does not match with Passowrd'
        else:
            cursor.execute( 'INSERT INTO tbl_customer (Password, CustomerName, PhoneNumber, Email) VALUES (%s, %s, %s, %s)', (PW, Name, PhoneNumber,Email))
            connection.commit()
            msg = 'You have successfully registered !'

    elif request.method == 'POST':
        msg = 'Please fill out the form !'

    return render_template('recSignUp.html', msg = msg)

@app.route('/pwChange')
def pwChange():
    if 'CustomerName' in session:
        return render_template('recChangePW.html')
    else:
        return redirect(url_for('signIn'))

@app.route('/pwChange/Submit', methods =['GET', 'POST'])
def pwChangeSubmit():
    if 'CustomerName' in session:
        msg = ''
        if request.method == 'POST' and 'Email' in request.form and 'PW' in request.form and 'ConfirmPW' in request.form and 'PhoneNumber' in request.form:
            PhoneNumber = request.form['PhoneNumber']
            Email = request.form['Email']
            PW = request.form['PW']
            ConfirmPW = request.form['ConfirmPW']

            connection.ping()
            cursor.execute('SELECT * FROM tbl_customer WHERE UserID = % s', session['UserID'])
            account = cursor.fetchone()

            if account['PhoneNumber'] != PhoneNumber and account['Email'] != Email:
                msg = 'Wrong credentials'
            elif request.form['ConfirmPW'] != request.form['PW']:
                msg = 'Confirm Password does not match with Passowrd'
            else:
                sql = 'UPDATE tbl_customer SET Password = %s WHERE UserID = %s'
                cursor.execute( sql, (PW, session['UserID']))
                connection.commit()
                msg = 'You have successfully registered !'

        return render_template('recChangePW.html', msg = msg)
    else:
        return redirect(url_for('signIn'))


@app.route('/recipe')
def recipe():
    if 'CustomerName' in session:
        return render_template('recSearch.html')
    else:
        return redirect(url_for('signIn'))

@app.route('/search', methods=['POST'])
def search():
    if 'CustomerName' in session:
        global hits_data
        includeIngredients = request.form.getlist('IngredientsCheck')
        minCalories = request.form['calories1']
        maxCalories = request.form['calories2']
        diet = request.form.getlist('DietsCheck')
        intolerances = request.form.getlist('HealthCheck')
        type = request.form.getlist('MealtypeCheck')

        # Construct the query string with the ingredients
        query = ''
        otherquery = ''
        if 'IngredientsCheck' in request.form:
            includeIngredientsStr = ','.join(includeIngredients)
            query += f'&includeIngredients={includeIngredientsStr}'

        if 'DietsCheck' in request.form:
            dietStr = ','.join(diet)
            otherquery += f'&diet={dietStr}'
                
        if 'HealthCheck' in request.form:
            intolerancesStr = ','.join(intolerances)
            otherquery += f'&intolerances={intolerancesStr}'

        if 'MealtypeCheck' in request.form:
            typeStr = ','.join(type)
            otherquery += f'&type={typeStr}'


        url = f'{URL}&apiKey={API_KEY}&number=20&instructionsRequired=True&addRecipeNutrition=True&addRecipeInformation=True{query}{otherquery}&calories={minCalories}-{maxCalories}'
        finalurl = url
        print(finalurl)

        # Make a GET request to the Edamam API
        response = requests.get(finalurl)
        response_content = response.text  # Extract the response content as a string
        data = json.loads(response_content)  # Parse the JSON string
        # data = response.json()

        hits = data['results']
        print(hits)
        hits_data = hits
        # return render_template('recipeResult.html', hits=hits)
        return redirect(url_for('recipeOutput'))
    
    else:
        redirect(url_for('signIn'))
    
@app.route('/recipeOutput')
def recipeOutput():
    if 'CustomerName' in session:
        global hits_data
        hits = hits_data
        return render_template('recResult.html', hits=hits)
    else:
        return redirect(url_for('signIn'))


@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    if 'CustomerName' in session:
        url = f'https://api.spoonacular.com/recipes/{recipe_id}/information?includeNutrition=True'
        params = {
            'apiKey': API_KEY,
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            recipe = response.json()
            return render_template('recView.html', recipe=recipe)
        return "Recipe not found", 404
    else:
        return redirect(url_for('signIn'))

@app.route('/error')
def searchError():
    if 'CustomerName' in session:
        return render_template('recipeError.html')
    else:
        return redirect(url_for('signIn'))
    
@app.route('/bookmark/<int:recipe_id>/<string:title>', methods=['POST'])
def bookmark(recipe_id, title):
    if 'CustomerName' in session:
        if request.method == 'POST':
            connection.ping()
            sql = 'INSERT INTO tbl_savedrecipe (UserID, ID, Title) VALUES (%s, %s, %s)'
            cursor.execute(sql, (session['UserID'], recipe_id, title))
            connection.commit()
            return redirect(url_for('view_recipe', recipe_id=recipe_id))
    else:
        return redirect(url_for('signIn'))
    
@app.route('/viewBookmark')
def viewBookmark():
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_savedrecipe WHERE UserID = %s"
        cursor.execute(sql, session['UserID'])
        rows = cursor.fetchall()
        return render_template('recbookmark.html', recipes=rows)
    else:
        return redirect(url_for('signIn'))
    
@app.route('/recipeSuggestion')
def recipeSuggestion():
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_recipesuggestion WHERE UserID = %s"
        cursor.execute(sql, session['UserID'])
        connection.commit()
        rows = cursor.fetchall()
        # admin = getAdminInfo(id)
        # return render_template('adminInventory.html', products=rows, admin = admin)
        return render_template('recSuggest.html', recipes=rows)
    else:
        return redirect(url_for('signIn'))
    
@app.route('/recipeSuggestion/view/<int:SuggestionID>', methods=['GET', 'POST'])
def viewSuggestion(SuggestionID):
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_recipesuggestion WHERE SuggestionID = %s"
        cursor.execute(sql, SuggestionID)
        connection.commit()
        rows = cursor.fetchall()
        # admin = getAdminInfo(id)
        # return render_template('adminInventory.html', products=rows, admin = admin)
        return render_template('recSuggestView.html', recipes=rows)
    else:
        return redirect(url_for('signIn'))
    
@app.route('/recipeSuggestion/add', methods =['GET', 'POST'])
def addSuggestion():
    if 'CustomerName' in session:
        # admin = getAdminInfo(id)
        if request.method == 'POST':
            connection.ping()
            RecipeName = request.form['RecipeName']
            Ingredients = request.form['Ingredients']
            Instructions = request.form['Instructions']
            RecipeImage = request.files['RecipeImage']

            UPLOAD_FOLDER = (r'D:\SCOPE\Year 3\Year 3 Coding\FYP\static\styles\recipe_photo')
            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            RecipeImage.save(os.path.join(app.config['UPLOAD_FOLDER'], RecipeImage.filename))

            sql = 'INSERT INTO tbl_recipesuggestion (UserID, RecipeName, Ingredients, Instructions, RecipeImage) VALUES (%s, %s, %s, %s, %s)'
            cursor.execute( sql, (session['UserID'], RecipeName, Ingredients, Instructions, RecipeImage.filename))
            connection.commit()

        return redirect(url_for('recipeSuggestion'))
    else:
        return redirect(url_for('signIn'))

@app.route('/recipeSuggestion/edit/<int:SuggestionID>', methods=['GET', 'POST'])
def editSuggestion(SuggestionID):
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_recipesuggestion WHERE SuggestionID = %s"
        cursor.execute(sql, SuggestionID)
        connection.commit()
        rows = cursor.fetchall()
        return render_template('recSuggestEdit.html', SuggestionID = SuggestionID, hits=rows)
    else:
        return redirect(url_for('signIn'))

@app.route('/recipeSuggestion/edit/submit', methods=['GET', 'POST'])
def editSuggestionSubmit():
    if 'CustomerName' in session:
        # admin = getAdminInfo(id)
        if request.method == 'POST':
            connection.ping()
            RecipeName = request.form['RecipeName']
            Ingredients = request.form['Ingredients']
            Instructions = request.form['Instructions']
            RecipeImage = request.files['RecipeImage']
            SuggestionID = request.form['SuggestionID']

            UPLOAD_FOLDER = (r'D:\SCOPE\Year 3\Year 3 Coding\FYP\static\styles\recipe_photo')
            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            RecipeImage.save(os.path.join(app.config['UPLOAD_FOLDER'], RecipeImage.filename))

            sql = 'UPDATE tbl_recipesuggestion SET UserID = %s, RecipeName = %s, Ingredients = %s, Instructions = %s, RecipeImage = %s WHERE SuggestionID = %s'
            cursor.execute( sql, (session['UserID'], RecipeName, Ingredients, Instructions, RecipeImage.filename, SuggestionID))
            connection.commit()

        return redirect(url_for('recipeSuggestion'))
    else:
        return redirect(url_for('signIn'))
    
@app.route('/grocery')
def grocery():
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_grocery WHERE UserID = %s"
        cursor.execute(sql, session['UserID'])
        connection.commit()
        rows = cursor.fetchall()
        # admin = getAdminInfo(id)
        # return render_template('adminInventory.html', products=rows, admin = admin)
        return render_template('recGrocery.html', recipes=rows)
    else:
        return redirect(url_for('signIn'))
    
@app.route('/grocery/view/<int:GroceryID>', methods=['GET', 'POST'])
def viewGrocery(GroceryID):
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_grocery WHERE GroceryID = %s"
        cursor.execute(sql, GroceryID)
        connection.commit()
        rows = cursor.fetchall()
        # admin = getAdminInfo(id)
        # return render_template('adminInventory.html', products=rows, admin = admin)
        return render_template('recGroceryView.html', recipes=rows)
    else:
        return redirect(url_for('signIn'))
    
@app.route('/grocery/add', methods =['GET', 'POST'])
def addGrocery():
    if 'CustomerName' in session:
        # admin = getAdminInfo(id)
        if request.method == 'POST':
            connection.ping()
            Ingredients = request.form['Ingredients']
            Notes = request.form['Notes']
            now = datetime.datetime.now()
            OrderDate =now.strftime("%Y-%m-%d")

            sql = 'INSERT INTO tbl_grocery (UserID, Date, Ingredients, Notes) VALUES (%s, %s, %s, %s)'
            cursor.execute( sql, (session['UserID'], OrderDate, Ingredients, Notes))
            connection.commit()

        return redirect(url_for('grocery'))
    else:
        return redirect(url_for('signIn'))

@app.route('/grocery/edit/<int:GroceryID>', methods=['GET', 'POST'])
def editGrocery(GroceryID):
    if 'CustomerName' in session:
        connection.ping()
        sql = "SELECT * FROM tbl_grocery WHERE GroceryID = %s"
        cursor.execute(sql, GroceryID)
        connection.commit()
        rows = cursor.fetchall()
        return render_template('recGroceryEdit.html', GroceryID = GroceryID, hits=rows)
    else:
        return redirect(url_for('signIn'))

@app.route('/grocery/edit/submit', methods=['GET', 'POST'])
def editGrocerySubmit():
    if 'CustomerName' in session:
        # admin = getAdminInfo(id)
        if request.method == 'POST':
            connection.ping()
            Ingredients = request.form['Ingredients']
            Notes = request.form['Notes']
            GroceryID = request.form['GroceryID']
            now = datetime.datetime.now()
            OrderDate =now.strftime("%Y-%m-%d")

            sql = 'UPDATE tbl_grocery SET UserID = %s, Date = %s, Ingredients = %s, Notes = %s WHERE GroceryID = %s'
            cursor.execute( sql, (session['UserID'], OrderDate, Ingredients, Notes, GroceryID))
            connection.commit()

        return redirect(url_for('grocery'))
    else:
        return redirect(url_for('signIn'))

@app.route('/signOut')
def signOut():
    session.pop('CustomerName', None)
    return redirect(url_for('signIn'))


if __name__ == "__main__":
    app.run(debug=True)