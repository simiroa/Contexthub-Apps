import webbrowser
import urllib.parse

class Integrations:
    @staticmethod
    def open_google_calendar(title, date_str, days=1.0):
        # https://www.google.com/calendar/render?action=TEMPLATE&text=...
        # date format: YYYYMMDD/YYYYMMDD
        try:
            start_dt = date_str.replace("-", "")
            # End date is start date + 1 day for all day event
            # Logic could be improved for half days but GCal is basic
            end_dt = start_dt 
            
            text = urllib.parse.quote(f"✈️ {title}")
            details = urllib.parse.quote(f"Vacation: {days} days")
            
            url = f"https://www.google.com/calendar/render?action=TEMPLATE&text={text}&details={details}&dates={start_dt}/{end_dt}"
            webbrowser.open(url)
        except:
            print("Failed to open calendar")
