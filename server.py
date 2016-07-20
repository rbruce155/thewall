from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import MySQLConnector
from flask_bcrypt import Bcrypt
import re

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'ShhDontTellAnyone'
mysql = MySQLConnector(app,'thewall')

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9\.\+_-]+@[a-zA-Z0-9\._-]+\.[a-zA-Z]*$')


@app.route('/')
def index():

	if not session.get('usrid'):
		return render_template("index.html")
	else:
		return redirect('/thewall')	

@app.route('/register', methods=['POST'])
def register():

	formInfo = request.form
	errors = 0

	for key, value in formInfo.iteritems():

		if len(value) < 1:
			print "no data on {}".format(key)
			errors+=1
			flash("Please fill out {}".format(key))
			
		
		elif key == "last_name":
			if not value.isalpha():
				print key + ": cannot contain any numbers"
				errors+=1
				flash("Last name must only contain letters")
			elif len(value) < 2:
				print key + ": must be more than 2 characters"
				errors+=1
				flash("Last name must be more than 2 characters") 	

		elif key == "fist_name":
			if not value.isalpha():
				print key + ": cannot contain any numbers"
				errors+=1
				flash("First name must only contain letters")
			elif len(value) < 2:
				print key + ": must be more than 2 characters"
				errors+=1
				flash("First name must be more than 2 characters")

		elif key == "email" and not EMAIL_REGEX.match(value):
			print key + ": not in correct email format"
			errors+=1
			flash("Email is not in the right format")

		elif key == "password" and len(value) < 8:
			print key + ": should be more than 8 characters"
			errors+=1
			flash("Password must be longer than 8 characters")	
			

	if formInfo['password'] != formInfo['confirm_password']:
		print "passwords dont match"
		errors+=1
		flash("Passwords do not match")
		

	if errors < 1:

		# get form values and set them to variables
		firstname = formInfo['first_name']
		lastname = formInfo['last_name']
		email = formInfo['email']
		password = formInfo['password']

		#check if user(email) exists
		check_query = "SELECT * FROM users WHERE email = :email limit 1"
		check_data = {'email': email}

		userMatch = mysql.query_db(check_query, check_data)

		if userMatch:
			flash(email + " already has an account")
			return redirect('/')

		else:	
			# generate password hash
			pw_hash = bcrypt.generate_password_hash(password)
			print "the key is" + pw_hash

			# create user
			create_query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (:first_name, :last_name, :email, :password, NOW(), NOW()) "

			create_data = {'first_name': firstname.title(), 'last_name': lastname.title(), 'email': email, 'password': pw_hash}

			mysql.query_db(create_query, create_data)


			# get new user info and set session to usr id
			newUsr_query = "SELECT * FROM users WHERE email = :email limit 1"
			newUsr_data = {'email': email}

			userInfo = mysql.query_db(newUsr_query, newUsr_data)

			session['usrid'] = userInfo[0]['id']

			return redirect('/thewall')

	else:
		return redirect('/')
				 		


@app.route('/login', methods=['POST'])
def login():
	
	# get form vars
	email = request.form['email']
	password = request.form['password']


	if len(email) < 1 or len(password) < 1:
		flash("Please enter values for email/password")
		return redirect('/')
	else:
	
		# get user info
		user_query = "SELECT * FROM users WHERE email = :email LIMIT 1"
		query_data = { 'email': email }
		user = mysql.query_db(user_query, query_data) # user will be returned in a list

		if not user:
			flash('There is no user that matches your search. Please try again or register to access the wall.')
			return redirect('/')
		else:	
			# compare password hashes
			if bcrypt.check_password_hash(user[0]['password'], password):
				# login user
				session['usrid'] = user[0]['id']
				print session['usrid']

				return redirect('/thewall')

			else:
			 	# set flash error message and redirect to login page
			 	flash("Password is incorrect, please try again.")
			 	return redirect('/')
	

@app.route('/thewall')
def thewall():

	if not session.get('usrid'):
		return redirect('/')

	else:

		# get user info
		userInfo_query = "SELECT * FROM users WHERE id = :id limit 1"
		userInfo_data = {'id': session['usrid']}

		userInfo = mysql.query_db(userInfo_query, userInfo_data)

		name = userInfo[0]['first_name']

		# get all user messages
		allUsrMessages_querry = "SELECT * FROM users u JOIN messages m ON m.user_id = u.id ORDER BY m.created_at DESC "
		allUsrMessages = mysql.query_db(allUsrMessages_querry)

		# get all comments
		allUsrComments_querry = "SELECT u.first_name 'first_name', u.last_name 'last_name', c.created_at 'created_at', c.comment 'comment', c.message_id 'message_id' FROM comments c JOIN users u, messages m WHERE c.user_id = u.id AND c.message_id = m.id ORDER BY c.created_at DESC"
		allUsrComments = mysql.query_db(allUsrComments_querry)
		
		return render_template("thewall.html", name=name, allUsrMessages=allUsrMessages, allUsrComments=allUsrComments)

		


@app.route('/post' , methods=['POST'])
def post():
	
	postText = request.form['newpost']

	
	if not postText:
		flash("You cannot submit a blank message")
		return redirect('/thewall')
	else:	
		#store in db
		newpost_query = "INSERT INTO messages(user_id, message, created_at, updated_at) VALUES (:user_id, :message, NOW(), NOW())"
		newpost_data = {'user_id': session['usrid'], 'message': postText}

		mysql.query_db(newpost_query, newpost_data)

		return redirect('/thewall')


@app.route('/logout')
def logout():
	
	session.clear()
	return redirect('/')
	
#whats better to use this method to pass id or in form... ask anna
@app.route('/comment/<message_id>', methods=['POST'])
def comment(message_id):	
	
	commentText = request.form['commentTxt']
	

	if not commentText:
		flash("You cannot submit blank comments..")

	else:
		#store comment in db
		newcomment_query = "INSERT INTO comments( message_id, user_id, comment, created_at, updated_at) VALUES (:message_id, :user_id, :comment, NOW(), NOW())"
		newcomment_data = {'message_id': message_id, 'user_id': session['usrid'], 'comment': commentText}

		mysql.query_db(newcomment_query, newcomment_data)

	
	return redirect('/thewall')



app.run(debug=True) # run our server