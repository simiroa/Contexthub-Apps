from datetime import datetime, date, timedelta

class UndoManager:
    def __init__(self, max_depth=20):
        self.stack = []
        self.redo_stack = []
        self.max_depth = max_depth

    def push(self, state):
        import copy
        self.stack.append(copy.deepcopy(state))
        if len(self.stack) > self.max_depth:
            self.stack.pop(0)
        self.redo_stack.clear()

    def undo(self, current_state):
        if not self.stack:
            return None
        import copy
        self.redo_stack.append(copy.deepcopy(current_state))
        return self.stack.pop()

    def redo(self, current_state):
        if not self.redo_stack:
            return None
        import copy
        self.stack.append(copy.deepcopy(current_state))
        return self.redo_stack.pop()

class LeaveManagerCore:
    def __init__(self, storage):
        self.storage = storage
        self.undo_mgr = UndoManager()

    def get_settings(self):
        data = self.storage.load_data()
        return data.get("settings", {})

    def save_settings(self, **kwargs):
        data = self.storage.load_data()
        for k, v in kwargs.items():
            data["settings"][k] = v
        self.storage.save_data(data)

    def get_leave_types(self):
        s = self.get_settings()
        return s.get("leave_types", [])

    def add_leave_type(self, type_name):
        data = self.storage.load_data()
        types = data["settings"].get("leave_types", [])
        if type_name and type_name not in types:
            types.append(type_name)
            data["settings"]["leave_types"] = types
            self.storage.save_data(data)

    def remove_leave_type(self, type_name):
        data = self.storage.load_data()
        types = data["settings"].get("leave_types", [])
        if type_name in types:
            types.remove(type_name)
            data["settings"]["leave_types"] = types
            self.storage.save_data(data)

    def get_history(self):
        data = self.storage.load_data()
        return data.get("history", [])

    def add_history_item(self, date_str, type_name, amount, note=""):
        data = self.storage.load_data()
        self.undo_mgr.push(data) # Save state before change
        
        # Ensure KST timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        item = {
            "date": date_str,
            "type": type_name,
            "amount": float(amount),
            "note": note,
            "timestamp": timestamp
        }
        data["history"].append(item)
        self.storage.save_data(data)

    def delete_history_item(self, index):
        # Legacy index-based deletion
        data = self.storage.load_data()
        if 0 <= index < len(data["history"]):
            del data["history"][index]
            self.storage.save_data(data)

    def delete_history_item_by_content(self, target_item):
        # Safe deletion finding the exact dict match
        data = self.storage.load_data()
        self.undo_mgr.push(data) # Save state before change
        
        # Find item that matches date, amount, note, type
        for i, item in enumerate(data["history"]):
             if (item.get("date") == target_item.get("date") and 
                 item.get("amount") == target_item.get("amount") and
                 item.get("note") == target_item.get("note") and
                 item.get("type") == target_item.get("type")):
                 del data["history"][i]
                 break
        self.storage.save_data(data)

    def get_current_leave_year_range(self):
        settings = self.get_settings()
        reset_date_str = settings.get("reset_date", "01-01") # MM-DD
        
        try:
            today = date.today()
            # Handle MM-DD or M-D
            parts = reset_date_str.split('-')
            month, day = int(parts[0]), int(parts[1])
            
            # This year's reset date
            this_year_reset = date(today.year, month, day)
            
            if today >= this_year_reset:
                start_date = this_year_reset
                end_date = date(today.year + 1, month, day) - timedelta(days=1)
            else:
                start_date = date(today.year - 1, month, day)
                end_date = this_year_reset - timedelta(days=1)
                
            return start_date.isoformat(), end_date.isoformat()
        except:
            # Fallback to calendar year
            year = date.today().year
            return f"{year}-01-01", f"{year}-12-31"

    def calculate_balance(self):
        settings = self.get_settings()
        total_days = float(settings.get("total_days", 15.0))  # 기본 연차
        
        start_date, end_date = self.get_current_leave_year_range()
        
        # Separate tracking for each pool
        annual_used = 0.0    # 연차 사용
        credit_added = 0.0   # 대체휴가 적립
        credit_used = 0.0    # 대체휴가 사용
        sick_used = 0.0      # 병가 사용
        usage_by_type = {}   # For calendar display
        
        for item in self.get_history():
            item_date = item.get("date")
            # Only count items within the current leave year range for balance
            if not (start_date <= item_date <= end_date):
                continue

            amt = float(item.get("amount", 0.0))
            type_name = item.get("type", "Other")
            type_lower = type_name.lower()
            
            if amt < 0:  # Usage
                abs_amt = abs(amt)
                # Aggregate by type for calendar
                if type_name not in usage_by_type:
                    usage_by_type[type_name] = 0.0
                usage_by_type[type_name] += abs_amt
                
                # Track by pool
                if "대체휴가" in type_name or "credit" in type_lower:
                    credit_used += abs_amt
                elif "병가" in type_name or "sick" in type_lower:
                    sick_used += abs_amt
                else:  # 연차 and others
                    annual_used += abs_amt
            else:  # Credit addition
                credit_added += amt
        
        # Calculate remaining for each pool
        annual_remaining = total_days - annual_used
        credit_remaining = credit_added - credit_used
        
        return {
            # Legacy support
            "total_initial": total_days,
            "total_added": credit_added,
            "total_used": annual_used + credit_used + sick_used,
            "remaining": annual_remaining + credit_remaining,
            "usage_by_type": usage_by_type,
            
            # New separate pool data
            "annual": {
                "total": total_days,
                "used": annual_used,
                "remaining": annual_remaining
            },
            "credit": {
                "total": credit_added,
                "used": credit_used,
                "remaining": credit_remaining
            },
            "sick": {
                "used": sick_used
            }
        }

    def get_expiration_warning(self):
        s = self.get_settings()
        exp = s.get("expiration_date", "")
        if not exp: return None, False
        try:
            today = date.today()
            if len(exp.split('-')) == 2:
                exp = f"{today.year}-{exp}"
            d_date = datetime.strptime(exp, "%Y-%m-%d").date()
            delta = (d_date - today).days
            if delta < 0: return delta, True
            return delta, (delta <= 30)
        except:
            return None, False

    def get_events_for_month(self, year, month):
        events = {}
        img = f"{year}-{month:02d}"
        for item in self.get_history():
            if item["date"].startswith(img):
                try:
                    d = int(item["date"].split("-")[2])
                    if d not in events: events[d] = []
                    events[d].append(item)
                except: pass
        return events

    def export_history_to_csv(self, filename):
        import csv
        data = self.get_history()
        if not data: return False
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Standardized headers
                writer.writerow(["Date", "Type", "Days", "Note", "CreatedAt"])
                for item in data:
                    writer.writerow([
                        item.get("date"),
                        item.get("type"),
                        abs(float(item.get("amount", 0))),
                        item.get("note"),
                        item.get("timestamp")
                    ])
            return True
        except Exception:
            return False

    def export_history_to_ics(self, filename):
        """Export history to iCalendar (.ics) format for external app compatibility."""
        from datetime import datetime, timedelta
        data = self.get_history()
        if not data: return False
        
        try:
            lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//ContextUp//Leave Manager//EN",
                "CALSCALE:GREGORIAN",
                "METHOD:PUBLISH"
            ]
            
            for idx, item in enumerate(data):
                # ISO date to YYYYMMDD
                dt_str = item.get("date").replace("-", "")
                type_name = item.get("type", "Vacation")
                note = item.get("note", "")
                amt = abs(float(item.get("amount", 0)))
                
                # UID should be unique
                uid = item.get("timestamp", f"{dt_str}_{idx}").replace(":", "").replace("-", "")
                
                lines.append("BEGIN:VEVENT")
                lines.append(f"UID:{uid}@contextup.leavemanager")
                lines.append(f"DTSTART;VALUE=DATE:{dt_str}")
                # End date is start date + 1 for all-day events in ICS
                end_dt = (datetime.strptime(item.get("date"), "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
                lines.append(f"DTEND;VALUE=DATE:{end_dt}")
                lines.append(f"SUMMARY:{type_name} ({amt}d)")
                lines.append(f"DESCRIPTION:{note}")
                lines.append("STATUS:CONFIRMED")
                lines.append("TRANSP:TRANSPARENT")
                lines.append("END:VEVENT")
                
            lines.append("END:VCALENDAR")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False

    def undo(self):
        current_data = self.storage.load_data()
        prev_data = self.undo_mgr.undo(current_data)
        if prev_data:
            self.storage.save_data(prev_data)
            return True
        return False

    def redo(self):
        current_data = self.storage.load_data()
        next_data = self.undo_mgr.redo(current_data)
        if next_data:
            self.storage.save_data(next_data)
            return True
        return False

    def get_next_upcoming_vacation(self):
        """Finds the nearest future vacation (amount < 0) from history."""
        from datetime import date
        today = date.today().isoformat()
        upcoming = []
        for item in self.get_history():
            # Check if it's usage (negative amount) and date is in future/today
            if item.get("amount", 0) < 0 and item.get("date") >= today:
                upcoming.append(item)
        
        if not upcoming:
            return None
            
        # Sort by date ascending to get the nearest one
        upcoming.sort(key=lambda x: x["date"])
        return upcoming[0]

    def calculate_end_date(self, start_date_str, duration_days):
        """Calculates end date given start date and duration."""
        try:
            dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            delta = int(duration_days) - 1 if int(duration_days) >= 1 else 0
            if duration_days < 1.0: delta = 0
            
            end_dt = dt + timedelta(days=delta)
            return end_dt.strftime("%Y-%m-%d")
        except:
            return start_date_str

    def is_public_holiday(self, year, month, day):
        """Checks if a given date is a public holiday using the 'holidays' library."""
        try:
            import holidays
            kr_holidays = holidays.KR(years=year)
            h_date = date(year, month, day)
            if h_date in kr_holidays:
                return kr_holidays.get(h_date)
            return None
        except ImportError:
            # Fallback to a minimal static list if library is missing
            h_str = f"{month:02d}-{day:02d}"
            static_holidays = {
                "01-01": "신정", "03-01": "삼일절", "05-05": "어린이날",
                "06-06": "현충일", "08-15": "광복절", "10-03": "개천절",
                "10-09": "한글날", "12-25": "성탄절"
            }
            return static_holidays.get(h_str)

    def get_preview_dates(self, start_date_str, duration_days):
        """Returns a list of date strings involved in this duration, skipping weekends and holidays."""
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            dates = []
            current = start_date
            count = 0.0 # Use float for count to handle partial days
            
            while count < duration_days:
                # Get holiday name for the current date
                holiday_name = self.is_public_holiday(current.year, current.month, current.day)
                
                # Skip weekends and public holidays
                if current.weekday() < 5 and not holiday_name:
                    dates.append(current.strftime("%Y-%m-%d"))
                    count += 1.0
                elif duration_days < 1.0: # Special case for partial days
                    # If the user requests a partial day (e.g., 0.5 days) and the start date
                    # is a weekend/holiday, we still want to count it as the requested day.
                    dates.append(current.strftime("%Y-%m-%d"))
                    count += 1.0 
                
                # Safety break to prevent infinite loop (limit to 2 years)
                if (current - start_date).days > 365 * 2:
                    break
                
                if count >= duration_days: break
                current += timedelta(days=1)
                
            return dates
        except Exception:
            return []

    def generate_html_report(self, filename):
        """Generates a premium, data-rich HTML dashboard report."""
        import json
        history = self.get_history()
        stats = self.calculate_balance()
        
        # Prepare data for charts
        monthly_usage = {} # "YYYY-MM" -> amount
        for item in history:
            if item.get("amount", 0) < 0:
                m = item["date"][:7]
                monthly_usage[m] = monthly_usage.get(m, 0) + abs(item["amount"])
        
        sorted_months = sorted(monthly_usage.keys())
        chart_labels = sorted_months
        chart_data = [monthly_usage[m] for m in sorted_months]

        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leave Manager Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Noto+Sans+KR:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --secondary: #a855f7;
            --bg: #0f172a;
            --card-bg: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', 'Noto Sans KR', sans-serif;
            background: radial-gradient(circle at top right, #1e1b4b, #0f172a);
            color: #f8fafc;
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{ text-align: center; margin-bottom: 50px; }}
        h1 {{ font-size: 3rem; font-weight: 800; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .glass {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{ text-align: center; padding: 25px; transition: transform 0.3s ease; }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-value {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 5px; color: #fff; }}
        .stat-label {{ font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
        .chart-container {{ margin-bottom: 40px; position: relative; height: 350px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ text-align: left; padding: 15px; color: #818cf8; border-bottom: 1px solid var(--border); font-size: 0.85rem; text-transform: uppercase; }}
        td {{ padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 0.95rem; }}
        tr:hover {{ background: rgba(255,255,255,0.02); }}
        .badge {{
            padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;
        }}
        .badge-annual {{ background: rgba(99, 102, 241, 0.2); color: #818cf8; }}
        .badge-credit {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
        footer {{ text-align: center; margin-top: 50px; color: #64748b; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Leave Manager Report</h1>
            <p style="color: #94a3b8; margin-top: 10px;">Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="stats-grid">
            <div class="glass stat-card">
                <div class="stat-value">{stats['annual']['remaining']:.1f}</div>
                <div class="stat-label">Remaining Annual</div>
            </div>
            <div class="glass stat-card">
                <div class="stat-value">{stats['annual']['used']:.1f}</div>
                <div class="stat-label">Used Annual</div>
            </div>
            <div class="glass stat-card">
                <div class="stat-value">{stats['credit']['remaining']:.1f}</div>
                <div class="stat-label">Credit Balance</div>
            </div>
            <div class="glass stat-card">
                <div class="stat-value">{stats['total_used']:.1f}</div>
                <div class="stat-label">Total Days Out</div>
            </div>
        </div>

        <div class="glass chart-container">
            <canvas id="usageChart"></canvas>
        </div>

        <div class="glass">
            <h2 style="margin-bottom: 20px; font-weight: 600;">Recent History</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Days</th>
                        <th>Note</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f"<tr><td>{item['date']}</td><td><span class='badge badge-{'annual' if 'annual' in item.get('type','').lower() or '연차' in item.get('type','') else 'credit'}'>{item['type']}</span></td><td>{abs(item['amount'])}</td><td>{item['note']}</td></tr>" for item in sorted(history, key=lambda x: x['date'], reverse=True)[:15]])}
                </tbody>
            </table>
        </div>

        <footer>
            &copy; {datetime.now().year} Leave Manager Pro. Built for ContextUp.
        </footer>
    </div>

    <script>
        const ctx = document.getElementById('usageChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    label: 'Monthly Leave Usage',
                    data: {json.dumps(chart_data)},
                    borderColor: '#818cf8',
                    backgroundColor: 'rgba(129, 140, 248, 0.2)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointBackgroundColor: '#818cf8',
                    borderWidth: 3
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: '#1e1b4b',
                        padding: 12,
                        titleFont: {{ size: 14 }},
                        bodyFont: {{ size: 13 }},
                        displayColors: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_template)
            return True
        except Exception:
            return False
