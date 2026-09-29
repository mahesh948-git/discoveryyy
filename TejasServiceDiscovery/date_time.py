from datetime import datetime

def current_date():
# Assuming 'ist' is a datetime object
    ist = datetime.now()
    ist_12hr_format = ist.strftime("%d_%b(%I-%M%p)")

    return ist_12hr_format
