from datetime import datetime, timedelta
import os
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    # If PyMySQL is not available, proceed; flask_mysqldb may still find MySQLdb
    pass

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor


app = Flask(__name__)

# MySQL configuration - update for your environment or via env vars
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'Nsairaju@7')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'hospital_kiosk')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    cr_number = request.form.get('cr_number', '').strip()
    if not cr_number:
        return jsonify({'status': 'error', 'message': 'CR Number is required'}), 400

    cursor = mysql.connection.cursor(DictCursor)

    cursor.execute(
        "SELECT cr_number, name, age, gender, doctor, department, last_visit FROM patients WHERE cr_number = %s",
        (cr_number,),
    )
    patient = cursor.fetchone()

    if not patient:
        return jsonify({'status': 'error', 'message': 'Invalid CR Number. Please contact helpdesk.'}), 404

    # Enforce revisit eligibility: last_visit must be within the last 14 days
    last_visit = patient.get('last_visit')
    if last_visit is None:
        return jsonify({'status': 'error', 'code': 'EXPIRED_14D', 'message': 'వాలిడిటీ సమయం పూర్తైంది. దయచేసి కొత్త రిజిస్ట్రేషన్ చేయించుకోండి.'}), 400

    try:
        # MySQLdb returns a date/datetime object; normalize to date for comparison
        last_visit_date = getattr(last_visit, 'date', lambda: last_visit)()
    except Exception:
        last_visit_date = last_visit

    try:
        days_since_last_visit = (datetime.now().date() - last_visit_date).days
    except Exception:
        return jsonify({'status': 'error', 'code': 'EXPIRED_14D', 'message': 'వాలిడిటీ సమయం పూర్తైంది. దయచేసి కొత్త రిజిస్ట్రేషన్ చేయించుకోండి.'}), 400

    if days_since_last_visit > 14:
        return jsonify({'status': 'error', 'code': 'EXPIRED_14D', 'message': 'వాలిడిటీ సమయం పూర్తైంది. దయచేసి కొత్త రిజిస్ట్రేషన్ చేయించుకోండి.'}), 400

    # Create an appointment 15 minutes from now
    appointment_time = datetime.now() + timedelta(minutes=15)

    cursor.execute(
        """
        INSERT INTO appointments (cr_number, doctor, appointment_time)
        VALUES (%s, %s, %s)
        """,
        (cr_number, patient['doctor'], appointment_time),
    )
    mysql.connection.commit()

    appointment_id = cursor.lastrowid

    return jsonify(
        {
            'status': 'success',
            'appointment_id': appointment_id,
            'name': patient['name'],
            'cr_number': patient['cr_number'],
            'age': patient['age'],
            'gender': patient['gender'],
            'doctor': patient['doctor'],
            'department': patient['department'],
            'appointment_time': appointment_time.strftime('%I:%M %p, %d-%b-%Y'),
        }
    )


@app.route('/print_slip/<int:appointment_id>')
def print_slip(appointment_id: int):
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute(
        """
        SELECT a.id, a.cr_number, a.doctor, a.appointment_time, p.name, p.department, p.age, p.gender
        FROM appointments a
        JOIN patients p ON p.cr_number = a.cr_number
        WHERE a.id = %s
        """,
        (appointment_id,),
    )
    appt = cursor.fetchone()

    if not appt:
        return redirect(url_for('index'))

    # Format time for display
    appt_time_display = appt['appointment_time'].strftime('%I:%M %p, %d-%b-%Y')
    valid_upto_time_display = (appt['appointment_time'] + timedelta(hours=5)).strftime('%I:%M %p, %d-%b-%Y')

    return render_template(
        'appointment.html',
        hospital_name='NIMS ',
        name=appt['name'],
        cr_number=appt['cr_number'],
        Age = appt['age'],
        Gender = appt['gender'],
        doctor=appt['doctor'],
        department=appt.get('department', ''),
        appointment_time_display=appt_time_display,
        valid_upto_time_display=valid_upto_time_display,
    )


# ---------- gTTS Telugu TTS ----------
try:
    from gtts import gTTS
    import io
except Exception:
    gTTS = None


@app.route('/tts', methods=['POST'])
def tts():
    # JSON { text: '...' } -> MP3 audio via gTTS (Telugu)
    payload = request.get_json(silent=True) or {}
    text = (payload.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'text required'}), 400
    if gTTS is None:
        return jsonify({'error': 'gtts_not_available'}), 503
    try:
        mp3_io = io.BytesIO()
        gTTS(text=text, lang='te').write_to_fp(mp3_io)
        mp3_io.seek(0)
        return send_file(mp3_io, mimetype='audio/mpeg', as_attachment=False, download_name='speech.mp3')
    except Exception as e:
        return jsonify({'error': 'tts_failed', 'detail': str(e)}), 500


@app.route('/say')
def say():
    # Query: /say?text=...&return=/next
    if gTTS is None:
        return redirect(request.args.get('return') or '/')
    text = (request.args.get('text') or '').strip()
    return_url = request.args.get('return') or '/'
    if not text:
        return redirect(return_url)
    try:
        mp3_io = io.BytesIO()
        gTTS(text=text, lang='te').write_to_fp(mp3_io)
        b64 = __import__('base64').b64encode(mp3_io.getvalue()).decode('ascii')
        # Minimal page to autoplay, with tap-to-play fallback and redirect
        html = (
            "<!DOCTYPE html>\n"
            "<html><head><meta charset=\"utf-8\"><title>Say</title>\n"
            "<style>body{margin:0;font-family:sans-serif;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh} .btn{font-size:22px;padding:16px 24px;background:#06c;color:#fff;border:none;border-radius:8px} .row{display:flex;gap:12px;flex-direction:column;align-items:center}</style>\n"
            "</head><body>\n"
            "<audio id=\"au\" autoplay playsinline src=\"data:audio/mpeg;base64," + b64 + "\"></audio>\n"
            "<div id=\"ui\" class=\"row\" style=\"display:none\"><div>\u0C2A\u0C4D\u0C32\u0C47 \u0C28\u0C4A\u0C15\u0C4D\u0C15\u0C3F \u0C2A\u0C4D\u0C32\u0C47 \u0C1A\u0C47\u0C2F\u0C02\u0C21\u0C3F.</div><button id=\"playBtn\" class=\"btn\">\u0C2A\u0C4D\u0C32\u0C47 \u0C1A\u0C47\u0C2F\u0C02\u0C21\u0C3F</button><button id=\"skipBtn\" class=\"btn\" style=\"background:#444\">\u0C35\u0C26\u0C4D\u0C26\u0C41\u0C32\u0C41</button></div>\n"
            "<script>\n"
            "const go=()=>window.location.href=" + repr(return_url) + ";\n"
            "const a=document.getElementById('au');const ui=document.getElementById('ui');const pb=document.getElementById('playBtn');const sb=document.getElementById('skipBtn');\n"
            "function showUI(){if(ui)ui.style.display='flex';}\n"
            "if(a){a.addEventListener('ended',go);a.addEventListener('error',showUI);}\n"
            "if(sb)sb.addEventListener('click',go);\n"
            "if(pb)pb.addEventListener('click',()=>{try{a&&a.play&&a.play().then(()=>{ui.style.display='none';}).catch(showUI)}catch(e){showUI()}});\n"
            "try{a&&a.play&&a.play().catch(()=>{showUI()})}catch(e){showUI()}\n"
            "try{history.replaceState(null,''," + repr(return_url) + ")}catch(e){}\n"
            "setTimeout(go,15000);\n"
            "</script></body></html>\n"
        )
        return html
    except Exception:
        return redirect(return_url)


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=True)



