# Import necessary libraries
import os
from flask import Flask, render_template, session, redirect, request, send_file, render_template_string, url_for
import pdfkit
import io
from docx import Document
import tempfile
import openai
import xlsxwriter
import openpyxl
import dotenv
import re
import pandas as pd
import numpy as np
import json
import psycopg2
from psycopg2.extras import execute_values
dotenv.load_dotenv()

# Create a Flask web application
app = Flask(__name__, static_url_path='/static')

# Set the secret key for session management
app.secret_key = "your_secret_key"  # Replace with your own secret key

# Simulated user data (replace with a real authentication system)
users = {'user1': 'password1', 'user2': 'password2'}
admin_user = {'AD': 'BC'}

# Database configuration
db_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'postgres',
    'user': 'postgres',
    'password': os.getenv('DB_PASS')
}

# Connect to the PostgreSQL database
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Initialize the OpenAI API client
openai.api_key = os.getenv('OPEN_AI_API')

# Define a route for the homepage
@app.route('/')
def login():
    return render_template('login.html')

# Define a route for user authentication
@app.route('/login', methods=['POST'])
def authenticate():
    username = request.form['username']
    password = request.form['password']

    if username in users and users[username] == password:
        session['username'] = username
        session['submission'] = ''
        session['gpt_response'] = ''
        return render_template('form.html', submission='', username=username)
    elif username in admin_user and admin_user[username] == password:
        session['username'] = username
        session['submission'] = ''
        session['gpt_response'] = ''
        return render_template('admin_landing_page.html', submission='', username=username)
    else:
        return "Authentication failed. <a href='/'>Try again</a>"

# User Interface routes

@app.route('/process_form', methods=['POST'])
def process_form():
    # Extract form data
    input = request.form['work']
    portfolio = request.form['project']
    service = request.form['services']
    selected_date = request.form['selected_date']
    progress = request.form['progress']
    team = request.form['team']

    # Use the OpenAI API to generate a response
    prompts = [
        {
            'role': 'system',
            'content': """
            You are a professional business report generator. Your task is to create a detailed business report in the following format, which includes sections for input, output, and a business update. Maintain a high level of professionalism in the language and presentation of the report.

            Please adhere to the specific format provided below:

            INPUT:
            Generate a 3-4 word long name for a response that focuses on the work done this week. Be concise.

            OUTPUT:
            Generate a concise one-line response that focuses on the outcome of the work done this week. Highlight aspects such as efficiency gains, reduced efforts, time savings, or other relevant results.

            BUSINESS UPDATE:
            Generate a succinct one-line statement that focuses on the updates related to the business from the generated output. Discuss how efficiency is improved, efforts are reduced, or any other pertinent updates that align with the organization's goals and objectives.
            """
        },
        {
            'role': 'user',
            'content': f"{input}"
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=prompts,
        temperature=0.0
    )

    gpt_response = response.choices[0].message.content

    # Store session data
    session['submission'] = gpt_response
    session['gpt_response'] = gpt_response
    session['portfolio'] = portfolio
    session['service'] = service
    session['selected_date'] = selected_date
    session['progress'] = progress
    session['team'] = team

    return redirect(url_for('submission_output_editable'))

@app.route('/submission_output_editable')
def submission_output_editable():
    text = session.get('gpt_response', '')
    print(text)

    input_pattern = r'INPUT:(.*?)OUTPUT:'
    output_pattern = r'OUTPUT:(.*?)BUSINESS UPDATE:'
    business_update_pattern = r'BUSINESS UPDATE:(.*)'

    # Use re.DOTALL to match across multiple lines
    input_match = re.search(input_pattern, text, re.DOTALL)
    output_match = re.search(output_pattern, text, re.DOTALL)
    business_update_match = re.search(business_update_pattern, text, re.DOTALL)

    # Extract the matched content
    input_section = input_match.group(1).strip() if input_match else ""
    output_section = output_match.group(1).strip() if output_match else ""
    business_update_section = business_update_match.group(1).strip() if business_update_match else ""

    return render_template('submission_output_editable.html', submission=session.get('submission', ''),
                           username=session.get('username', ''), input=input_section, output=output_section,
                           business_update=business_update_section)

@app.route('/update_submission', methods=['POST'])
def update_submission():
    text = session.get('submission', '')
    portfolio = session.get('portfolio', '')
    service = session.get('service', '')
    input_data = request.form.get('input')
    output_data = request.form.get('output')
    business_update = request.form.get('bu')

    input_pattern = r'INPUT:(.*?)OUTPUT:'
    output_pattern = r'OUTPUT:(.*?)BUSINESS UPDATE:'
    business_update_pattern = r'BUSINESS UPDATE:(.*)'

    # Use re.DOTALL to match across multiple lines
    input_match = re.search(input_pattern, text, re.DOTALL)
    output_match = re.search(output_pattern, text, re.DOTALL)
    business_update_match = re.search(business_update_pattern, text, re.DOTALL)

    # Extract the matched content
    input_section = input_match.group(1).strip() if input_match else ""
    output_section = output_match.group(1).strip() if output_match else ""
    business_update_section = business_update_match.group(1).strip() if business_update_match else ""

    # Write the submission to the PostgreSQL database
    cursor.execute(
        "INSERT INTO weekreport (DATE_COLUMN,USERNAME,INPUT_,OUTPUT_,BUSINESS_UPDATE,SERVICE ,PORTFOLIO,TEAMMATES,PROGRESS) VALUES (%s,%s,%s, %s,%s,%s,%s,%s,%s)",
        (session['selected_date'], session['username'], input_data, output_data, business_update, service, portfolio, session['team'],session['progress']))
    conn.commit()
    session.pop('username', None)
    session.pop('submission', None)

    return redirect(url_for('login'))

# Admin Interface routes

@app.route('/portfolio_details', methods=['GET', 'POST'])
def portfolio_details():
    # Fetch Portfolio details
    # Fetch Portfolio details from the database
    conn = psycopg2.connect(**db_config)
    todate = request.form['toDate']
    session['todate'] = todate
    fromdate = request.form['fromDate']
    session['fromdate'] = fromdate
    portfolio = request.form['project']
    session['portfolio'] = portfolio
    service = request.form['services']
    session['service'] = service

    query = ''
    df = ''

    if portfolio == 'all':
        query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND SERVICE LIKE '{service}'"
        df = pd.read_sql(query, conn)
    else:
        query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND PORTFOLIO LIKE '{portfolio}' AND SERVICE LIKE '{service}'"
        df = pd.read_sql(query, conn)

    conn = psycopg2.connect(**db_config)
    portfolio = session.get('portfolio', '')
    query = f"SELECT BUSINESS_UPDATE FROM allreport "
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()

    portfolio_details = result[0] if result else ''

    string_format = ""
    for num in range(0, len(df)):
        if num == 0:
            string_format = string_format + "\n" + f"""
            {df.iloc[num]['portfolio']}

            {df.iloc[num]['input_']}
            - {df.iloc[num]['output_']}
        """
        elif (num > 0 and df.iloc[num - 1]['portfolio'] != df.iloc[num]['portfolio']):
            string_format = string_format + "\n" + f"""
            {df.iloc[num]['portfolio']}

            {df.iloc[num]['input_']}
            - {df.iloc[num]['output_']}
        """
        else:
            string_format = string_format + "\n" + f"""
            {df.iloc[num]['input_']}
            - {df.iloc[num]['output_']}
        """

    portfolio_details = string_format

    return render_template_string(render_template('portfolio_details.html', portfolio_details=portfolio_details))

@app.route('/updated_portfolio_details', methods=['GET', 'POST'])
def update_portfolio_details():
    portfolio_details = request.form.get('portfolio-textarea')
    session["portfolio-textarea"] = portfolio_details

    return render_template_string(render_template('updated_portfolio_details.html', portfolio_details=portfolio_details))

@app.route('/download_portfolio_docx', methods=['POST'])
def download_portfolio_docx():
    portfolio_details = session.get('portfolio-textarea', '')

    doc = Document()
    doc.add_heading('Portfolio Details', level=1)
    doc.add_paragraph(portfolio_details)

    temp_docx_file = io.BytesIO()
    doc.save(temp_docx_file)
    temp_docx_file.seek(0)

    return send_file(
        temp_docx_file,
        as_attachment=True,
        download_name='portfolio_details.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/report')
def report():
    # Define logic to generate and render the report.html page
    # This can include fetching data and rendering the template
    return render_template('report.html')

@app.route('/excel', methods=['POST'])
def index():
    conn = psycopg2.connect(**db_config)
    todate = request.form['toDate']
    session['todate'] = todate
    fromdate = request.form['fromDate']
    session['fromdate'] = fromdate
    portfolio = request.form['project']
    session['portfolio'] = portfolio
    service = request.form['services']
    session['service'] = service

    query = ''
    df = ''

    if portfolio == 'all':
        query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND SERVICE LIKE '{service}'"
        df = pd.read_sql(query, conn)
    else:
        query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND PORTFOLIO LIKE '{portfolio}' AND SERVICE LIKE '{service}'"
        df = pd.read_sql(query, conn)

    conn.close()

    table_html = df.to_html(classes='table table-bordered table-striped', index=False)

    return render_template('report.html', table_html=table_html)

@app.route('/download_xlsx', methods=['GET', 'POST'])
def download_xlsx():
    portfolio = session.get('portfolio', '')
    service = session.get('service', '')
    fromdate = session.get('fromdate', '')
    todate = session.get('todate', '')
    conn = psycopg2.connect(**db_config)

    query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND PORTFOLIO LIKE '{portfolio}' AND SERVICE LIKE '{service}'"
    df = pd.read_sql(query, conn)

    temp_dir = tempfile.mkdtemp()

    xlsx_file_path = os.path.join(temp_dir, 'data.xlsx')
    with pd.ExcelWriter(xlsx_file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)

    return send_file(xlsx_file_path, as_attachment=True, download_name='data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    portfolio = session.get('portfolio', '')
    service = session.get('service', '')
    fromdate = session.get('fromdate', '')
    todate = session.get('todate', '')
    conn = psycopg2.connect(**db_config)
    query = f"SELECT * FROM weekreport WHERE DATE_COLUMN BETWEEN '{fromdate}' AND '{todate}' AND PORTFOLIO LIKE '{portfolio}' AND SERVICE LIKE '{service}'"
    df = pd.read_sql(query, conn)

    conn.close()

    table_html = df.to_html(classes='table table-bordered table-striped', index=False)
    rendered_html = render_template('report_pdf.html', table_html=table_html)

    pdf_options = {
        'page-size': 'A4',
        'orientation': 'portrait',
        'no-outline': True,
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
    }

    pdf = pdfkit.from_string(rendered_html, False, options=pdf_options)

    return send_file(
        io.BytesIO(pdf),
        as_attachment=True,
        download_name='report.pdf',
        mimetype='application/pdf'
    )

# Run the Flask app if this file is executed directly
if __name__ == '__main__':
    app.run(debug=False , host='0.0.0.0')
