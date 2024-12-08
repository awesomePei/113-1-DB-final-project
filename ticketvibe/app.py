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

# user 查詢演唱會
@app.route('/user_search_concert')
def user_search_concert():
    from datetime import datetime

    current_time = datetime.now()

    # Print current time for debugging
    print(f"Current time: {current_time}")

    query = '''
        SELECT * FROM public."CONCERT"
        WHERE "time" > %s
    '''
    concerts = execute_query(query, (current_time,), fetch_all=True)

    # Print concerts for debugging
    print(f"Concerts found: {concerts}")

    return render_template('user_search_concert.html', concerts=concerts)

    return render_template('user_search_concert.html', concerts=concerts)

# buy ticket 選演唱會
@app.route('/buy_ticket_concert', methods=['GET', 'POST'])
def buy_ticket_concert():
    if 'user_id' not in session:
        flash("You must be logged in to buy a ticket.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        concert_name = request.form.get('concert_name')
        concert_time = request.form.get('concert_time')
        session['selected_concert'] = {'name': concert_name, 'time': concert_time}
        return redirect(url_for('buy_ticket_seat'))

    concerts_query = 'SELECT name, "time" FROM public."CONCERT"'
    concerts = execute_query(concerts_query, fetch_all=True)
    return render_template('buy_ticket_concert.html', concerts=concerts)

# buy ticket 選座位
@app.route('/buy_ticket_seat', methods=['GET', 'POST'])
def buy_ticket_seat():
    if 'user_id' not in session or 'selected_concert' not in session:
        flash("Please select a concert first.", "danger")
        return redirect(url_for('buy_ticket_concert'))

    concert = session['selected_concert']
    if request.method == 'POST':
        seat_id = request.form.get('seatID')
        session['selected_seat'] = seat_id
        return redirect(url_for('buy_ticket_payment'))

    seats_query = '''
        SELECT "seatID", price 
        FROM public."SEAT_PRICE" sp
        WHERE sp.concert_name = %s AND sp.concert_time = %s
        AND NOT EXISTS (
            SELECT 1 
            FROM public."TICKET" t 
            WHERE t."seatID" = sp."seatID" 
            AND t.concert_name = sp.concert_name
            AND t.concert_time = sp.concert_time
            AND t.refund_status = False  -- 確保票券尚未退款
        )
        '''

    seats = execute_query(seats_query, (concert['name'], concert['time']), fetch_all=True)

    return render_template('buy_ticket_seat.html', seats=seats, concert=concert)

#buy ticket 付款方式
@app.route('/buy_ticket_payment', methods=['GET', 'POST'])
def buy_ticket_payment():
    if 'user_id' not in session or 'selected_seat' not in session:
        flash("Please select a seat first.", "danger")
        return redirect(url_for('buy_ticket_seat'))

    if request.method == 'POST':
        payment_method = request.form.get('payment')
        session['payment_method'] = payment_method
        return redirect(url_for('confirm_ticket'))

    return render_template('buy_ticket_payment.html')

#confirm ticket
@app.route('/confirm_ticket', methods=['GET', 'POST'])
def confirm_ticket():
    if 'user_id' not in session or 'payment_method' not in session:
        flash("Please complete the ticket selection process.", "danger")
        return redirect(url_for('buy_ticket_payment'))

    user_id = session['user_id']
    concert = session['selected_concert']
    seat_id = session['selected_seat']
    payment_method = session['payment_method']

    timing_query = """
        SELECT presale_time, public_sale_time
        FROM public."CONCERT"
        WHERE name = %s AND "time" = %s
    """
    timing = execute_query(timing_query, (concert['name'], concert['time']), fetch_one=True)

    if not timing:
        flash("Concert timing information is unavailable.", "danger")
        return redirect(url_for('buy_ticket_concert'))

    presale_time = timing['presale_time']
    public_time = timing['public_sale_time']

    # 判断 ticket_type
    current_time_query = "SELECT NOW() AS current_time"
    current_time = execute_query(current_time_query, fetch_one=True)['current_time']

    if presale_time <= current_time < public_time:
        ticket_type = "Presale"
    elif current_time >= public_time:
        ticket_type = "Public"
    else:
        error_message = "Tickets are not on sale at this time."
        return render_template('confirm_ticket.html', 
                               concert=concert, 
                               seat_id=seat_id, 
                               payment=payment_method, 
                               error_message=error_message)


    if request.method == 'POST':
        ticket_id_query = 'SELECT COALESCE(MAX("ticketID"), 0) + 1 AS new_id FROM public."TICKET"'
        new_ticket_id = execute_query(ticket_id_query, fetch_one=True)['new_id']
        
        # 先默認 ticket type 是 public
        # ticket_type = "Public"

        refund_deadline_query = "SELECT CURRENT_DATE + INTERVAL '7 days' AS refund_ddl"
        refund_deadline = execute_query(refund_deadline_query, fetch_one=True)['refund_ddl']
        print("yes")
        # Prepare the query to insert the ticket into the database
        insert_query = """
            INSERT INTO public."TICKET" 
            ("ticketID", collected, "seatID", type, order_time, refund_ddl, refund_status, payment, "userID", concert_name, concert_time)
            VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s)
        """
        try:
            execute_query(insert_query, (
                new_ticket_id, False, seat_id, ticket_type, refund_deadline, False, payment_method, user_id, concert['name'], concert['time']
            ))
            flash("Ticket purchased successfully!", "success")
            response = redirect(url_for('my_ticket'))
            print("Redirect response: ", response)
            return response
        except Exception as e:
            flash(f"Error purchasing ticket: {e}", "danger")

    return render_template('confirm_ticket.html', concert=concert, seat_id=seat_id, payment=payment_method)

# my ticket
@app.route('/my_ticket')
def my_ticket():
    if 'user_id' not in session:
        flash("You must be logged in to view your tickets.", "danger")
        return redirect(url_for('login'))

    # Query to get the current time from the database
    current_time_query = "SELECT NOW()::date AS current_time"  # Convert to date directly in SQL
    current_time = execute_query(current_time_query, fetch_one=True)['current_time']

    user_id = session['user_id']
    query = '''
        SELECT t."ticketID", t."seatID", t.type, t.payment, t.order_time, t.collected, t.refund_status, t.refund_ddl, c.name AS concert_name, c."time" AS concert_time 
        FROM public."TICKET" t
        JOIN public."CONCERT" c ON t.concert_name = c.name AND t.concert_time = c."time"
        WHERE t."userID" = %s
        ORDER BY t.order_time DESC
    '''
    tickets = execute_query(query, (user_id,), fetch_all=True)

    return render_template('my_ticket.html', tickets=tickets, current_time=current_time)


@app.route('/refund_ticket/<int:ticket_id>', methods=['GET', 'POST'])
def refund_ticket(ticket_id):
    # 確保用戶已登入
    if 'user_id' not in session:
        flash("You must be logged in to refund a ticket.", "danger")
        return redirect(url_for('login'))

    # 查詢票券資訊
    user_id = session['user_id']
    ticket_query = '''
        SELECT t.*, t.refund_ddl FROM public."TICKET" t
        WHERE t."ticketID" = %s AND t."userID" = %s AND t.refund_status = False
    '''
    ticket = execute_query(ticket_query, (ticket_id, user_id), fetch_one=True)

    # 如果票券不存在或無法退款，返回錯誤
    if not ticket:
        flash("Invalid ticket or ticket cannot be refunded.", "danger")
        return redirect(url_for('my_ticket'))

    # 確認當前時間是否在 refund_ddl 之前
    current_time_query = "SELECT NOW() AS current_time"
    current_time = execute_query(current_time_query, fetch_one=True)['current_time']
    refund_ddl = ticket['refund_ddl']

    if current_time > refund_ddl:
        flash("Refund period has expired. You cannot refund this ticket.", "danger")
        return redirect(url_for('my_ticket'))

    if request.method == 'POST':
        # 執行退款
        refund_query = '''
            UPDATE public."TICKET"
            SET refund_status = True
            WHERE "ticketID" = %s
        '''
        try:
            execute_query(refund_query, (ticket_id,))
            flash("Ticket refunded successfully!", "success")
        except Exception as e:
            flash(f"Error refunding ticket: {e}", "danger")
        return redirect(url_for('my_ticket'))

    # 渲染退款確認頁面
    return render_template('refund_ticket.html', ticket=ticket)


#############################################################################################################

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

        print(concert_name, seat_id, price)

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

# 查詢使用者
@app.route('/search_user', methods=['GET', 'POST'])
def search_user():
    # 如果是 POST 請求，執行搜尋
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        
        # 根據搜尋條件查詢用戶（使用LIKE進行模糊匹配）
        user_query = '''
            SELECT * FROM public."USERS"
            WHERE userid LIKE %s OR email LIKE %s
        '''
        # 執行查詢並過濾結果
        users = execute_query(user_query, ('%' + search_query + '%', '%' + search_query + '%'), fetch_all=True)

        # 返回搜尋結果到模板
        return render_template('search_user.html', users=users)

    # 如果是 GET 請求，則列出所有使用者
    users_query = '''SELECT * FROM public."USERS";'''
    users = execute_query(users_query, fetch_all=True)

    # 返回所有使用者到模板
    return render_template('search_user.html', users=users)



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

