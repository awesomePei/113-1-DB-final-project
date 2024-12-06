from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import execute_query

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a secure key

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# 註冊頁面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['userid']
        name = request.form['username']
        phone = request.form['phonenum']
        email = request.form['email']
        password = request.form['pwd']
        isAdmin = False  # Default to regular user

        query = """
            INSERT INTO public."USERS" (userid, username, phone, email, password, isAdmin)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        try:
            execute_query(query, (user_id, name, phone, email, password, isAdmin))
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except:
            flash("Registration failed. User ID may already exist.", "danger")

    return render_template('register.html')

# 登入頁面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['userid']
        password = request.form['pwd']

        query = """SELECT * FROM public."USERS" WHERE userid = %s;"""
        user = execute_query(query, (user_id,), fetch_one=True)

        if user and user['password'] == password:
            session['user_id'] = user['userid']
            session['isadmin'] = user['isadmin']
            flash("Login successful!", "success")
            if user['isadmin']:  # If the user is an admin, redirect to admin dashboard
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash("Invalid user ID or password.", "danger")

    return render_template('login.html')

# 購票頁面
@app.route('/purchase_ticket', methods=['GET', 'POST'])
def purchase_ticket():
    if 'user_id' not in session:
        flash("Please log in to purchase tickets.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        concert_name = request.form['concert_name']
        concert_time = request.form['concert_time']
        seat_id = request.form['seat_id']
        payment = request.form['payment']

        query = """
            INSERT INTO TICKET (userID, concert_name, concert_time, seatID, payment, order_time)
            VALUES (%s, %s, %s, %s, %s, NOW());
        """
        execute_query(query, (user_id, concert_name, concert_time, seat_id, payment))
        flash("Ticket purchased successfully!", "success")
        return redirect(url_for('index'))

    return render_template('purchase_ticket.html')

# admin 新增演唱會
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if the user is logged in and is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Admin submits the form to add a new concert
        concert_name = request.form['concert_name']
        concert_time = request.form['concert_time']
        PR_capacity = request.form['pr_capacity']
        presale_capacity = request.form['presale_capacity']
        public_capacity = request.form['public_capacity']
        venue_address = request.form['venue_address']
        host_phone = request.form['host_phone']
        presale_time = request.form['presale_time']
        public_sale_time = request.form['public_sale_time']

        query = """
            INSERT INTO public."CONCERT" (name, "time", "PR_capacity", presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        execute_query(query, (concert_name, concert_time, PR_capacity, presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time))
        flash("Concert added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html')  # This is the admin page with a form to add a concert


# 登出頁面
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

