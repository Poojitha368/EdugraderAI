from flask import Flask,render_template,session,request,flash,redirect,url_for
from flask_mysqldb import MySQL
from flask_session import Session
# changes 
import google.generativeai as genai
import json

# Configure Gemini API # changes
genai.configure(api_key="AIzaSyB7IZ1lx8TuJ8KKyLs3XK7wvBDIr9PdTwU")
model = genai.GenerativeModel('gemini-1.5-flash')

#changes
def get_gemini_grade_feedback(question, paragraph):
    input_prompt = f'''
    You are an expert grader. Please evaluate the following answer based on the given question. 
    Provide a grade (out of 10) and give constructive feedback in 50 words.
    
    Question: {question}
    
    Answer: {paragraph}
    '''
    response = model.generate_content([input_prompt])
    
    # Log the raw response for debugging
    print("API Response:", response.text)
    
    # Extract grade and feedback from the plain text response
    try:
        response_text = response.text.strip()
        
        # Find the grade in the response
        grade_start = response_text.find("Grade: ") + len("Grade: ")
        grade_end = response_text.find("/10", grade_start)
        grade = response_text[grade_start:grade_end].strip()

        # Find the feedback in the response
        feedback_start = response_text.find("\n", grade_end) + 1
        feedback = response_text[feedback_start:].strip()
        
        return grade, feedback
    except Exception as e:
        print(f"Error extracting grade and feedback: {str(e)}")
        return None, "Error parsing the response"


app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Needed for flashing messages

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'edugrader'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")


        # session["username"] = username
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO user(username, password, email) VALUES (%s, %s, %s)", (username, password, email))
        mysql.connection.commit()
        cur.close()
        return redirect("/")
    return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cur = mysql.connection.cursor()
        cur.execute("SELECT username,id,password FROM user WHERE username = %s AND password = %s", (username, password))
        existing_user = cur.fetchone()
        cur.close()

        if existing_user:
            session["username"] = username
            session["id"]=existing_user[1]
            flash("login successfull",'success')
            return redirect("/grading")
        else:
            flash('Invalid credentials, please try again.', 'danger')

    return render_template("login.html")


@app.route('/grading', methods=["POST", "GET"])
def grading():
    if not session.get("username"):
        return redirect("/login")
    
    if request.method == "POST":
        question = request.form.get("question").strip()
        answer = request.form.get("answer").strip()

        # Validate inputs
        if not question or not answer:
            flash("Both question and answer fields are required.", "danger")
            return render_template('grading.html')

        print("Received question:", question)  # Debugging statement
        print("Received answer:", answer)  # Debugging statement

        id = session.get("id")
        cur = mysql.connection.cursor()
        marks, feedback = get_gemini_grade_feedback(question, answer)
        print("Marks:", marks)  # Debugging statement
        print("Feedback:", feedback)  # Debugging statement
        
        if marks and feedback:
            cur.execute("INSERT INTO history(question, answer, user_id, marks, feedback) VALUES (%s, %s, %s, %s, %s)", (question, answer, id, marks, feedback))
            mysql.connection.commit()
            cur.close()
            return render_template('grading.html', marks=marks, feedback=feedback, question=question, answer=answer)
        else:
            flash('Error in grading process. Please try again.', 'danger')
            cur.close()
            return render_template('grading.html')

    return render_template('grading.html')


@app.route("/profile")
def profile():
    username = session.get("username")
    if not username:
        return redirect('/login')
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT username, email FROM user WHERE username = %s", (username,))
    profile_details = cur.fetchone()
    
    if profile_details:
        email = profile_details[1]  # email should be index 1
        username = profile_details[0]  # username should be index 0
        cur.close()
        return render_template('profile.html', username=username, email=email)
    else:
        cur.close()
        return redirect('/login')




@app.route("/logout")
def logout():
    session["username"] = None
    return redirect("/")

# @app.route("/update_profile")
# def update_profile():
#     return 

@app.route('/subscribe')
def subscribe():
    if not session.get("username"):
        return redirect("/login")
    return render_template('subscribe.html')

@app.route('/history')
def history():
    if not session.get("username"):
        return redirect("/login")
    id = session.get('id')
    cur = mysql.connection.cursor()
    cur.execute("SELECT question, answer,marks,feedback,qno FROM history WHERE user_id = %s", (id,))
    history = cur.fetchall()
    cur.close()
    return render_template('history.html',history=history)

@app.route('/delete/<int:qno>', methods=['POST'])
def delete(qno):
    if not session.get("username"):
        return redirect("/login")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM history WHERE qno = %s", (qno,))
    mysql.connection.commit()
    cur.close()
    return redirect('/history')




if __name__ == '__main__':
    app.run(debug=True)
