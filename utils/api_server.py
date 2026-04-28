"""
Simple HTTP API server for Zap Bot — allows remote commands via web dashboard.
Runs on port 5000.

Usage:
    python -m utils.api_server
    Then visit: http://localhost:5000
"""

import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import os
import sys

# Add parent to path so we can import bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gmail_client import send_email
from utils.ai_client import generate_work_order_response
from config import BUSINESS_EMAIL, BUSINESS_PHONE, TIMEZONE

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# Simple in-memory log for dashboard
command_log = []

def log_command(action: str, status: str, details: str = ""):
    """Log a command execution."""
    command_log.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details
    })
    # Keep last 50 commands
    if len(command_log) > 50:
        command_log.pop()


@app.route('/')
def dashboard():
    """Serve the web dashboard."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zap Bot Control Panel</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            h1 { color: #2E7D32; }
            .section { margin-bottom: 30px; padding: 15px; border-left: 4px solid #2E7D32; background: #f9f9f9; }
            input, textarea, button { font-size: 14px; padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #2E7D32; color: white; cursor: pointer; }
            button:hover { background: #1b5e20; }
            .log { background: #f0f0f0; padding: 15px; border-radius: 4px; max-height: 400px; overflow-y: auto; }
            .log-item { margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #2E7D32; }
            .status-success { color: green; }
            .status-error { color: red; }
            .status { font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Zap Bot Control Panel</h1>

            <div class="section">
                <h2>📧 Send Email</h2>
                <input type="email" id="email_to" placeholder="Recipient email" />
                <input type="text" id="email_subject" placeholder="Subject" />
                <textarea id="email_body" placeholder="Email body" rows="4"></textarea>
                <button onclick="sendEmail()">Send Email</button>
                <div id="email_result"></div>
            </div>

            <div class="section">
                <h2>📅 Create Booking (Square)</h2>
                <input type="text" id="booking_customer" placeholder="Customer name" />
                <input type="email" id="booking_email" placeholder="Customer email" />
                <input type="text" id="booking_address" placeholder="Service address" />
                <input type="datetime-local" id="booking_time" />
                <textarea id="booking_notes" placeholder="Service notes" rows="3"></textarea>
                <button onclick="createBooking()">Create Booking</button>
                <div id="booking_result"></div>
            </div>

            <div class="section">
                <h2>⚙️ Bot Status</h2>
                <button onclick="getBotStatus()">Check Status</button>
                <div id="status_result"></div>
            </div>

            <div class="section">
                <h2>📋 Command History</h2>
                <div class="log" id="command_log"></div>
            </div>
        </div>

        <script>
            function sendEmail() {
                const to = document.getElementById('email_to').value;
                const subject = document.getElementById('email_subject').value;
                const body = document.getElementById('email_body').value;

                if (!to || !subject || !body) {
                    alert('Please fill in all fields');
                    return;
                }

                fetch('/api/send_email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ to, subject, body })
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('email_result').innerHTML =
                        data.success
                            ? '<p class="status-success">✓ Email sent!</p>'
                            : '<p class="status-error">✗ Error: ' + data.error + '</p>';
                    updateLog();
                });
            }

            function createBooking() {
                const customer = document.getElementById('booking_customer').value;
                const email = document.getElementById('booking_email').value;
                const address = document.getElementById('booking_address').value;
                const time = document.getElementById('booking_time').value;
                const notes = document.getElementById('booking_notes').value;

                if (!customer || !email || !address || !time) {
                    alert('Please fill in required fields');
                    return;
                }

                fetch('/api/create_booking', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ customer, email, address, time, notes })
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('booking_result').innerHTML =
                        data.success
                            ? '<p class="status-success">✓ Booking created!</p>'
                            : '<p class="status-error">✗ Error: ' + data.error + '</p>';
                    updateLog();
                });
            }

            function getBotStatus() {
                fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status_result').innerHTML =
                        '<p><strong>Status:</strong> ' + data.status + '</p>' +
                        '<p><strong>Uptime:</strong> ' + data.uptime + '</p>' +
                        '<p><strong>Last check:</strong> ' + data.last_check + '</p>';
                });
            }

            function updateLog() {
                fetch('/api/command_log')
                .then(r => r.json())
                .then(data => {
                    const log = document.getElementById('command_log');
                    log.innerHTML = data.log.map(item =>
                        '<div class="log-item">' +
                        '<span>' + item.timestamp.slice(11, 19) + '</span> ' +
                        '<strong>' + item.action + '</strong> ' +
                        '<span class="status ' + (item.status === 'success' ? 'status-success' : 'status-error') + '">' +
                        item.status.toUpperCase() + '</span>' +
                        (item.details ? '<p>' + item.details + '</p>' : '') +
                        '</div>'
                    ).join('');
                });
            }

            // Update log on load and every 5 seconds
            updateLog();
            setInterval(updateLog, 5000);
        </script>
    </body>
    </html>
    """
    return html


@app.route('/api/send_email', methods=['POST'])
def api_send_email():
    """Send an email on demand."""
    try:
        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')

        if not all([to, subject, body]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        send_email(to, subject, body)
        log_command('Send Email', 'success', f'To: {to}')
        return jsonify({'success': True})
    except Exception as e:
        log_command('Send Email', 'error', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/create_booking', methods=['POST'])
def api_create_booking():
    """Create a Square booking."""
    try:
        data = request.json
        customer = data.get('customer')
        email = data.get('email')
        address = data.get('address')
        time_str = data.get('time')
        notes = data.get('notes', '')

        # TODO: Integrate with Square API
        # For now, send confirmation email
        body = f"""
        <p>New booking created:</p>
        <p><strong>Customer:</strong> {customer}</p>
        <p><strong>Address:</strong> {address}</p>
        <p><strong>Time:</strong> {time_str}</p>
        <p><strong>Notes:</strong> {notes}</p>
        <p>Please confirm this booking in your system.</p>
        """

        send_email(BUSINESS_EMAIL, f'New Booking: {customer} - {address}', body)
        log_command('Create Booking', 'success', f'{customer} at {address}')
        return jsonify({'success': True})
    except Exception as e:
        log_command('Create Booking', 'error', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """Get bot status."""
    from datetime import datetime, timedelta
    import pytz

    tz = pytz.timezone(TIMEZONE)
    now = tz.localize(datetime.now())

    return jsonify({
        'status': 'Online',
        'uptime': 'Running',
        'last_check': now.strftime('%Y-%m-%d %H:%M:%S %Z')
    })


@app.route('/api/command_log')
def api_command_log():
    """Get recent command log."""
    return jsonify({'log': command_log})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
