from flask import Flask, render_template, request, redirect, url_for, session

import os

import openai

import xlsxwriter

import openpyxl

import dotenv

import re

 

dotenv.load_dotenv()

app = Flask(__name__)

app.secret_key = "your_secret_key"  # Replace with your own secret key

 

# Simulated user data (replace with a real authentication system)

users = {'user1': 'password1' , 'user2':'password2'}

api_key = os.getenv("OPEN_AI_API")

 

# Initialize the OpenAI API client

openai.api_key = api_key

 

# Excel file settings

excel_filename = 'submissions.xlsx'

 

def write_submission_to_excel(username, input, output, bis_upd , portfolio , service):

    # Load the existing Excel workbook using openpyxl

    if os.path.isfile(excel_filename):

        workbook = openpyxl.load_workbook(excel_filename)

    else:

        workbook = openpyxl.Workbook()

        sheet = workbook.active

        sheet.append(['USERNAME', 'INPUT', 'OUTPUT', 'BUSINESS UPDATE', 'SERVICE' , 'PORTFOLIO'])

 

    # Get the active sheet

    sheet = workbook.active

 

    # Find the next empty row

    row = sheet.max_row + 1

 

    # Write the submission data to the next row

    sheet.cell(row=row, column=1, value=username)

    sheet.cell(row=row, column=2, value=input)

    sheet.cell(row=row, column=3, value=output)

    sheet.cell(row=row, column=4, value=bis_upd)

    sheet.cell(row=row, column=5, value=service)

    sheet.cell(row=row, column=6, value=portfolio)

 

    # Save the workbook

    workbook.save(excel_filename)

 

def read_existing_data(filename):

    existing_data = []

 

    # Check if the file exists

    if os.path.isfile(filename):

        workbook = openpyxl.load_workbook(filename)

        sheet = workbook.active

 

        for row in sheet.iter_rows(min_row=2, values_only=True):

            existing_data.append(row)

 

    return existing_data

portfolio = ''

service = ''

gpt_response = ''

@app.route('/')

def login():

    return render_template('login.html')

 

@app.route('/login', methods=['POST'])

def authenticate():

    username = request.form['username']

    password = request.form['password']

 

    if username in users and users[username] == password:

        session['username'] = username

        session['submission'] = ''

        session['gpt_response'] = ''

        return render_template('form.html', submission='', username=username)

    else:

        return "Authentication failed. <a href='/'>Try again</a>"

 

 

@app.route('/process_form', methods=['POST'])

def process_form():

    input = request.form['work']

    portfolio = request.form['project']

    service = request.form['services']

    

 

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

        temperature = 0.0

          # Adjust as needed

    )

 

 

    gpt_response = response.choices[0].message.content

 

    session['submission'] = gpt_response

    session['gpt_response'] = gpt_response

    session['portfolio'] =  portfolio

    session['service'] = service

    

 

    return redirect(url_for('submission_output_editable'))

 

@app.route('/submission_output_editable' )

def submission_output_editable():

    text = session.get('gpt_response', '')

    print(text)

    input_pattern = r'INPUT:(.*?)OUTPUT:'

    output_pattern = r'OUTPUT:(.*?)BUSINESS UPDATE:'

    business_update_pattern = r'BUSINESS UPDATE:(.*)'

 

    # Use re.DOTALL to match across multiple lines

    input_match= re.search(input_pattern, text, re.DOTALL)

    output_match = re.search(output_pattern, text, re.DOTALL)

    business_update_match = re.search(business_update_pattern, text, re.DOTALL)

 

    # Extract the matched content

    input_section = input_match.group(1).strip() if input_match else ""

    output_section = output_match.group(1).strip() if output_match else ""

    business_update_section = business_update_match.group(1).strip() if business_update_match else ""

 

    return render_template('submission_output_editable.html', submission=session.get('submission', ''), username=session.get('username', ''),input = input_section, output=output_section, business_update=business_update_section)

 

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

    input_match= re.search(input_pattern, text, re.DOTALL)

    output_match = re.search(output_pattern, text, re.DOTALL)

    business_update_match = re.search(business_update_pattern, text, re.DOTALL)

 

    # Extract the matched content

    input_section = input_match.group(1).strip() if input_match else ""

    output_section = output_match.group(1).strip() if output_match else ""

    business_update_section = business_update_match.group(1).strip() if business_update_match else ""

 

    

 

 

 

# Write the submission to the Excel file

    write_submission_to_excel(session['username'], input_data, output_data, business_update , portfolio , service)

    session.pop('username', None)

    session.pop('submission', None)

 

    return redirect(url_for('login'))

 

if __name__ == '__main__':

    app.run(debug=False)
