from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import execute_query

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a secure key

# 主頁
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
                return redirect(url_for('index'))
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

# NEW 購票頁面
@app.route('/buy_ticket', methods=['GET', 'POST'])
def buy_ticket():
    if 'user_id' not in session:  # Check if user is logged in
        flash("You must be logged in to buy a ticket.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        seat_id = request.form.get('seatID')
        ticket_type = request.form.get('type')
        payment_method = request.form.get('payment')
        user_id = session['user_id']
        concert_name = request.form.get('concert_name')
        concert_time = request.form.get('concert_time')

        # Generate ticket ID (getting the max ticketID + 1)
        ticket_id_query = 'SELECT COALESCE(MAX("ticketID"), 0) + 1 AS new_id FROM public."TICKET"'
        new_ticket_id = execute_query(ticket_id_query, fetch_one=True)['new_id']
        
        # Refund deadline query (7 days from now)
        refund_deadline_query = "SELECT CURRENT_DATE + INTERVAL '7 days' AS refund_ddl"
        refund_deadline = execute_query(refund_deadline_query, fetch_one=True)['refund_ddl']

        # Prepare the query to insert the ticket into the database
        insert_query = """
            INSERT INTO public."TICKET" 
            ("ticketID", collected, "seatID", type, order_time, refund_ddl, refund_status, payment, "userID", concert_name, concert_time)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s)
        """
        try:
            execute_query(insert_query, (
                new_ticket_id, False, seat_id, ticket_type, refund_deadline, 0, payment_method, user_id, concert_name, concert_time
            ))
            flash("Ticket purchased successfully!", "success")
            return redirect(url_for('my_tickets'))
        except Exception as e:
            flash(f"Error purchasing ticket: {e}", "danger")

    # Fetch available concerts and seats
    concerts_query = 'SELECT name, "time" FROM public."CONCERT"'
    seats_query = 'SELECT "seatID", price FROM public."SEAT_PRICE"'
    concerts = execute_query(concerts_query, fetch_all=True)
    seats = execute_query(seats_query, fetch_all=True)

    return render_template('buy_ticket.html', concerts=concerts, seats=seats)

# admin 面板
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
            INSERT INTO public."CONCERT" (name, time, PR_capacity, presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        execute_query(query, (concert_name, concert_time, PR_capacity, presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time))
        flash("Concert added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html')  # This is the admin page with a form to add a concert

# admin 新增演唱會
@app.route('/add_concert', methods=['GET', 'POST'])
def add_concert():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if the user is logged in and is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Admin submits the form to add a new concert
        concert_name = request.form['concert_name']
        concert_time = request.form['concert_time']
        PR_capacity = request.form['PR_capacity']
        presale_capacity = request.form['presale_capacity']
        public_capacity = request.form['public_capacity']
        venue_address = request.form['venue_address']
        host_phone = request.form['host_phone']
        presale_time = request.form['presale_time']
        public_sale_time = request.form['public_sale_time']

        query = """
            INSERT INTO public."CONCERT" (name, time, "PR_capacity", presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        execute_query(query, (concert_name, concert_time, PR_capacity, presale_capacity, public_capacity, venue_address, host_phone, presale_time, public_sale_time))
        flash("Concert added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_concert.html')  # This will render the form for adding a new concert

# admin 新增 host
@app.route('/add_host', methods=['GET', 'POST'])
def add_host():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if the user is logged in and is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        person_in_charge = request.form['person_in_charge']

        query = """
            INSERT INTO public."HOST" (name, phone, email, person_in_charge)
            VALUES (%s, %s, %s, %s);
        """
        try:
            execute_query(query, (name, phone, email, person_in_charge))
            flash("Host added successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except:
            flash("Error adding host. Please try again.", "danger")

    return render_template('add_host.html')

# admin 新增 venue
@app.route('/add_venue', methods=['GET', 'POST'])
def add_venue():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if the user is logged in and is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        address = request.form['address']
        name = request.form['name']
        capacity = request.form['capacity']
        phone = request.form['phone']

        query = """
            INSERT INTO public."VENUE" (address, name, capacity, phone)
            VALUES (%s, %s, %s, %s);
        """
        try:
            execute_query(query, (address, name, capacity, phone))
            flash("Venue added successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except:
            flash("Error adding venue. Please try again.", "danger")

    return render_template('add_venue.html')

# admin 新增 performer
@app.route('/add_performer', methods=['GET', 'POST'])
def add_performer():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if the user is logged in and is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        performerID = request.form['performerID']
        name = request.form['name']
        company_name = request.form['company_name']
        company_phone = request.form['company_phone']

        query = """
            INSERT INTO public."PERFORMER" ("performerID", name, company_name, company_phone)
            VALUES (%s, %s, %s, %s)
        """
        try:
            execute_query(query, (performerID, name, company_name, company_phone))
            flash("Performer added successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except:
            flash("Error adding venue. Please try again.", "danger")

    return render_template('add_performer.html')

# admin 註冊 performer 在某場 concert 中 perform
@app.route('/register_performance', methods=['GET', 'POST'])
def register_performance():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if user is admin
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        performerID = request.form['performerID']
        concert_name = request.form['concert_name']
        concert_time = request.form['concert_time']

        query = """
            INSERT INTO public."PERFORM" ("performerID", concert_name, concert_time)
            VALUES (%s, %s, %s)
        """
        try:
            execute_query(query, (performerID, concert_name, concert_time))
            flash("Performance registered successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f"Error registering performance: {str(e)}", "danger")

    # Define your queries
    performers_query = """SELECT "performerID", name FROM public."PERFORMER" """
    concerts_query = """SELECT name, "time" FROM public."CONCERT" """

    # Fetch data using execute_query
    performers = execute_query(performers_query, fetch_all=True)
    concerts = execute_query(concerts_query, fetch_all=True)

    return render_template('register_performance.html', performers=performers, concerts=concerts)

# admin 定票價
@app.route('/set_seat_price', methods=['GET', 'POST'])
def set_seat_price():
    if 'user_id' not in session or not session.get('isadmin'):  # Check if admin is logged in
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        concert_name = request.form.get('concert_name')
        concert_time = request.form.get('concert_time')
        seat_id = request.form.get('seatID')
        price = request.form.get('price')

        query = """
            INSERT INTO public."SEAT_PRICE" (concert_name, concert_time, "seatID", price)
            VALUES (%s, %s, %s, %s)
        """
        try:
            execute_query(query, (concert_name, concert_time, seat_id, price))
            flash("Seat price set successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f"Error setting seat price: {e}", "danger")

    # Fetch available concerts for the form dropdown
    concerts_query = 'SELECT name, "time" FROM public."CONCERT"'
    concerts = execute_query(concerts_query, fetch_all=True)
    return render_template('set_seat_price.html', concerts=concerts)


# 查詢演唱會
@app.route('/search_concert')
def search_concert():
    query = """SELECT * FROM public."CONCERT";"""
    concerts = execute_query(query, fetch_all=True)
    return render_template('search_concert.html', concerts=concerts)


# 登出頁面
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

