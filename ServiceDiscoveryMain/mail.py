import ssl
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# SMTP server configuration
smtp_server = 'smtp.office365.com'
port = 587
email_password = "Projects@1"
sender_email = 'oss-reports@tfiber.in'

def send_mail_2(recipients, cc_recipients, subject, body, filename1, filename2, filename3):
    # Create the server connection
    context = ssl.create_default_context()
    server = smtplib.SMTP(smtp_server, port)
    server.starttls(context=context)
    server.login(sender_email, email_password)

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = ', '.join(recipients)
    if cc_recipients:
        message['Cc'] = ', '.join(cc_recipients)
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # attach first file
    if filename1:
        with open(filename1, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename1}',
            )
            message.attach(part)

    # attach second file
    if filename2:
        with open(filename2, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename2}',
            )
            message.attach(part)

        # attach third file
    if filename3:
        with open(filename3, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename3}',
            )
            message.attach(part)

    all_recipients = recipients + cc_recipients
    server.sendmail(sender_email, all_recipients, message.as_string())
    server.quit()
    print("sent mail .. ")


def send_mail(recipients,cc_recipients, subject,  body, filename):
    # Create the server connection
    context = ssl.create_default_context()
    server = smtplib.SMTP(smtp_server, port)
    server.starttls(context=context)
    server.login(sender_email, email_password)

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = ', '.join(recipients)
    if cc_recipients:
        message['Cc'] = ', '.join(cc_recipients)
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    if filename:
        with open(filename, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            message.attach(part)

    all_recipients = recipients + cc_recipients
    # Send the email
    server.sendmail(sender_email, all_recipients, message.as_string())
    server.quit()
    print("sent mail .. ")


