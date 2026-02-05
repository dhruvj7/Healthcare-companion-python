# app/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_patient_email(appointment_data: Dict) -> Dict[str, str]:
    """Generate patient confirmation email"""
    
    slot = appointment_data['slot']
    
    subject = f"Appointment Confirmed - {slot['doctor_name']} - {slot['slot_date']}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">✅ Appointment Confirmed!</h1>
        </div>
        
        <!-- Main Content -->
        <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            
            <p style="font-size: 16px; margin-bottom: 20px;">Dear <strong>{appointment_data['patient_name']}</strong>,</p>
            
            <p style="font-size: 16px; margin-bottom: 25px;">
                Great news! Your appointment has been successfully confirmed. Here are your appointment details:
            </p>
            
            <!-- Appointment Details Card -->
            <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 25px; border-radius: 8px; margin: 25px 0;">
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">📅</span>
                            <strong>Date:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['slot_date']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">🕒</span>
                            <strong>Time:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['slot_time']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">⏱️</span>
                            <strong>Duration:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['duration_minutes']} minutes
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">👨‍⚕️</span>
                            <strong>Doctor:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['doctor_name']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">🏥</span>
                            <strong>Specialty:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['doctor_specialty']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <span style="font-size: 20px; margin-right: 10px;">📍</span>
                            <strong>Location:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['location']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0;">
                            <span style="font-size: 20px; margin-right: 10px;">🔖</span>
                            <strong>Booking ID:</strong>
                        </td>
                        <td style="padding: 10px 0; text-align: right;">
                            <code style="background-color: rgba(0,0,0,0.1); padding: 5px 10px; border-radius: 4px; font-weight: bold;">
                                {appointment_data['booking_id']}
                            </code>
                        </td>
                    </tr>
                </table>
                
            </div>
            
            <!-- What to Bring Section -->
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    📋 What to Bring
                </h3>
                <ul style="line-height: 2; color: #555;">
                    <li>Valid photo ID (Driver's License, Passport, etc.)</li>
                    <li>Insurance card (if applicable)</li>
                    <li>List of current medications you're taking</li>
                    <li>Any relevant medical records or test results</li>
                    <li>Your payment method for copay</li>
                </ul>
            </div>
            
            <!-- Important Reminders Section -->
            <div style="margin: 25px 0;">
                <h3 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                    ⚠️ Important Reminders
                </h3>
                <ul style="line-height: 2; color: #555;">
                    <li><strong>Arrive 10-15 minutes early</strong> for check-in and paperwork</li>
                    <li>If you need to <strong>cancel or reschedule</strong>, please notify us at least <strong>24 hours in advance</strong></li>
                    <li>Bring a mask if you have any cold or flu symptoms</li>
                    <li>Contact us immediately if you develop fever or symptoms before your appointment</li>
                </ul>
            </div>
            
            <!-- Contact Information -->
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea;">
                <h3 style="margin-top: 0; color: #667eea;">Need to Contact Us?</h3>
                <p style="margin: 5px 0;">
                    <strong>Phone:</strong> <a href="tel:+15551234567" style="color: #667eea; text-decoration: none;">+1 (555) 123-4567</a>
                </p>
                <p style="margin: 5px 0;">
                    <strong>Email:</strong> <a href="mailto:{slot['doctor_email']}" style="color: #667eea; text-decoration: none;">{slot['doctor_email']}</a>
                </p>
            </div>
            
            <p style="font-size: 16px; margin-top: 30px;">
                We look forward to seeing you on <strong>{slot['slot_date']}</strong>!
            </p>
            
            <p style="margin-top: 20px;">
                Best regards,<br>
                <strong>{slot['doctor_name']}'s Office</strong>
            </p>
            
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; text-align: center; border: 1px solid #e0e0e0; border-top: none;">
            <p style="margin: 0; font-size: 12px; color: #666;">
                This is an automated confirmation email. Please do not reply directly to this message.
            </p>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                © 2026 Healthcare Appointment System. All rights reserved.
            </p>
        </div>
        
    </body>
    </html>
    """
    
    return {
        "subject": subject,
        "body_html": body_html
    }


def generate_doctor_email(appointment_data: Dict) -> Dict[str, str]:
    """Generate doctor notification email"""
    
    slot = appointment_data['slot']
    
    subject = f"New Appointment - {appointment_data['patient_name']} - {slot['slot_date']}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📅 New Appointment Scheduled</h1>
        </div>
        
        <!-- Main Content -->
        <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            
            <p style="font-size: 16px; margin-bottom: 20px;">Dear Dr. {slot['doctor_name'].split('Dr. ')[-1]},</p>
            
            <p style="font-size: 16px; margin-bottom: 25px;">
                A new appointment has been scheduled with you. Please review the details below:
            </p>
            
            <!-- Patient Information Card -->
            <div style="background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%); padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #11998e;">
                <h3 style="margin-top: 0; color: #00695c;">👤 Patient Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Name:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {appointment_data['patient_name']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Email:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            <a href="mailto:{appointment_data['patient_email']}" style="color: #00695c; text-decoration: none;">
                                {appointment_data['patient_email']}
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">
                            <strong>Phone:</strong>
                        </td>
                        <td style="padding: 8px 0; text-align: right;">
                            <a href="tel:{appointment_data['patient_phone']}" style="color: #00695c; text-decoration: none;">
                                {appointment_data['patient_phone']}
                            </a>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Appointment Details Card -->
            <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #f57c00;">
                <h3 style="margin-top: 0; color: #e65100;">📋 Appointment Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Date:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['slot_date']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Time:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['slot_time']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Duration:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['duration_minutes']} minutes
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Location:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            {slot['location']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <strong>Type:</strong>
                        </td>
                        <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1); text-align: right;">
                            <span style="background-color: rgba(0,0,0,0.1); padding: 5px 10px; border-radius: 4px; font-weight: bold;">
                                {appointment_data['appointment_type'].upper()}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;">
                            <strong>Booking ID:</strong>
                        </td>
                        <td style="padding: 8px 0; text-align: right;">
                            <code style="background-color: rgba(0,0,0,0.1); padding: 5px 10px; border-radius: 4px; font-weight: bold;">
                                {appointment_data['booking_id']}
                            </code>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Chief Complaint Section -->
            <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #8e24aa;">
                <h3 style="margin-top: 0; color: #6a1b9a;">🩺 Chief Complaint</h3>
                <p style="margin: 0; font-size: 16px; color: #4a148c; background-color: rgba(255,255,255,0.5); padding: 15px; border-radius: 4px;">
                    {appointment_data['reason_for_visit']}
                </p>
            </div>
            
            <!-- Status Notice -->
            <div style="background-color: #e8f5e9; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #4caf50;">
                <p style="margin: 0; color: #2e7d32;">
                    ✅ <strong>Status:</strong> The patient has been notified via email and has received confirmation details.
                </p>
            </div>
            
            <p style="margin-top: 30px;">
                Best regards,<br>
                <strong>Appointment Booking System</strong>
            </p>
            
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; text-align: center; border: 1px solid #e0e0e0; border-top: none;">
            <p style="margin: 0; font-size: 12px; color: #666;">
                This is an automated notification from the Healthcare Appointment System.
            </p>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                © 2026 Healthcare Appointment System. All rights reserved.
            </p>
        </div>
        
    </body>
    </html>
    """
    
    return {
        "subject": subject,
        "body_html": body_html
    }


def send_email(to: str, subject: str, body_html: str) -> bool:
    """
    Send email via SMTP (Gmail)
    
    Set these environment variables:
    - SMTP_EMAIL: Your Gmail address
    - SMTP_PASSWORD: App-specific password
    """
    
    smtp_email = os.getenv('SMTP_FROM_EMAIL')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        logger.warning("⚠️ SMTP credentials not set. Email content logged below:")
        logger.info(f"To: {to}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body preview: {body_html[:300]}...")
        logger.info("=" * 80)
        return True  # Return True in dev mode
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Appointment System <{smtp_email}>"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Attach HTML
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)
        
        # Send via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent to {to}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to}: {e}", exc_info=True)
        return False


async def send_confirmation_emails(appointment_data: Dict) -> bool:
    """Generate and send confirmation emails to both patient and doctor"""
    
    try:
        # Generate patient email
        patient_email = generate_patient_email(appointment_data)
        
        # Generate doctor email
        doctor_email = generate_doctor_email(appointment_data)
        
        # Send to patient
        patient_sent = send_email(
            to=appointment_data['patient_email'],
            subject=patient_email['subject'],
            body_html=patient_email['body_html']
        )
        
        # Send to doctor
        doctor_sent = send_email(
            to=appointment_data['slot']['doctor_email'],
            subject=doctor_email['subject'],
            body_html=doctor_email['body_html']
        )
        
        return patient_sent and doctor_sent
        
    except Exception as e:
        logger.error(f"Error sending confirmation emails: {e}", exc_info=True)
        return False