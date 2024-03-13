import ephem
import pytz
import json
import datetime
import base64, io
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from plotly.io import to_html
from flask import jsonify
from flask import Flask, render_template, request
from timezonefinder import TimezoneFinder

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def enter_location():
    locations = {
        'Raleigh': {'lat': '35.778573253959344', 'lon': '-78.63071172555289', 'title': "Raleigh, NC"},
        'Lebanon': {'lat': '43.642228293307404', 'lon': '-72.25019032094313', 'title': "Lebanon, NH"},
        'Louisville': {'lat': '38.2518079753768', 'lon': '-85.7625400989331', 'title': "Louisville, KY"},
        'San Francisco': {'lat': '37.77509867604425', 'lon': '-122.4205839151118', 'title': "San Francisco, CA"},
        'Los Angeles': {'lat': '34.05605617337469', 'lon': '-118.21462741989377', 'title': "Los Angeles, CA"},
        'Paris': {'lat': '48.85585130060084', 'lon': '2.3576733375945578', 'title': "Paris, France"},
        'Sydney': {'lat': '-33.870305862316044', 'lon': '151.20288490697737', 'title': "Sydney, Australia"},
        'Fairbanks': {'lat': '64.83987333213788', 'lon': '-147.71568025773414', 'title': "Fairbanks, AK"},
        'North Pole': {'lat': '90', 'lon': '0', 'title': "North Pole"},
        'South Pole': {'lat': '-90', 'lon': '0', 'title': "South Pole"},
        'Null island': {'lat': '0', 'lon': '0', 'title': "Null Island"},
        'Istanbul': {'lat': '41.00341731671383', 'lon': '28.984699128656757', 'title': "Istanbul, Turkey"},
        'Pittsburgh': {'lat': '40.43998536720357', 'lon': '-79.99695032749644', 'title': "Pittsburgh, PA"},
        'TromsØ': {'lat': '69.64923536347172', 'lon': '18.954377736088254', 'title': "Tromsø, Norway"},
        'Pune': {'lat': '18.525233995738027', 'lon': '73.85747387515629', 'title': "Pune, India"},
        'Beijing': {'lat': '39.91478688875563', 'lon': '116.39459944227269', 'title': "Beijing, China"}
    }

    if request.method == 'POST':
        selected_location = request.form.get('location-dropdown')

    lat = ''
    lon = ''
    title = ''

    if request.method == 'POST':
        selected_location = request.form.get('location-dropdown')
        if selected_location:
            lat = locations[selected_location]['lat']
            lon = locations[selected_location]['lon']
            title = locations[selected_location]['title']
        else:
            lat = request.form.get('lat')
            lon = request.form.get('lon')
            title = request.form.get('title')

    locations_json = json.dumps(locations) # Convert the locations dictionary to a JSON string
    # Convert locations to HTML dropdown options
    options_html = ''.join(f'<option value="{key}">{key.title()}</option>' for key in locations.keys())

    return f'''
        <form method="POST", onsubmit="event.preventDefault(); resetDropdown(); this.submit();">
            <select id="location-dropdown" id="location-dropdown" name="location-dropdown" onchange="updateFields()">
                <option value="">Select a location</option>
                {options_html}
            </select><br>
            Latitude: <input type="text" name="lat" id="lat" value="{lat}"><br>
            Longitude: <input type="text" name="lon" id="lon" value="{lon}"><br>
            Title: <input type="text" name="title" id="title" value="{title}"><br>
            <input type="submit" value="Submit">
        </form>
        <iframe src="/sunrise_sunset?lat={lat}&lon={lon}&title={title}" width="100%" height="600"></iframe>
        <script>
            var locations = {locations_json};
            function updateFields() {{
                var dropdown = document.getElementById('location-dropdown');
                var selectedLocation = dropdown.value;
                if (selectedLocation) {{
                    var latElement = document.getElementById('lat');
                    if (!latElement) {{
                        console.error('Element with id "lat" not found');
                    }} else if (!locations || !locations[selectedLocation]) {{
                        console.error('Location not found: ' + selectedLocation);
                    }} else {{
                        latElement.value = locations[selectedLocation]['lat'];
                        document.getElementById('lon').value = locations[selectedLocation]['lon'];
                        document.getElementById('title').value = locations[selectedLocation]['title'];
                    }}
                }}
            }}
            function resetDropdown() {{
                document.getElementById('location-dropdown').value = "";
            }}
        </script>
    '''

@app.route('/sunrise_sunset', methods=['GET'])
def sunrise_sunset():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    title = request.args.get('title')

    # Check if any of the fields are empty
    if not lat or not lon:
        return "Latitude and longitude are required"

    fig = generate_sunrise_sunset_plot(lat, lon, title)
    return to_html(fig, full_html=False)

def generate_sunrise_sunset_plot(lat, lon, title):
    # Set the observer's location
    observer = ephem.Observer()
    observer.lat = lat
    observer.lon = lon

    # Set the start and end dates for which you want to calculate the sunrise and sunset times
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 12, 31)

    # Get the timezone for the given latitude and longitude
    tf = TimezoneFinder()
    tz_str = tf.timezone_at(lat=float(lat), lng=float(lon))
    local_tz = pytz.timezone(tz_str)

    # Initialize lists to store the dates and times
    dates = []
    sunrise_times = []
    sunset_times = []
    standard_time_sunrise_times = []
    standard_time_sunset_times = []
    daylight_saving_time_sunrise_times = []
    daylight_saving_time_sunset_times = []

    current_date = start_date
    while current_date <= end_date:
        current_datetime = datetime.datetime.combine(current_date, datetime.datetime.min.time())
        date = ephem.Date(current_date)

        def handle_sun_event(observer, event_func, date, local_tz):
            try:
                event = event_func(ephem.Sun(), start=date)
            except (ephem.NeverUpError, ephem.AlwaysUpError):
                return None, None, None

            try:
                event_local = event.datetime() + local_tz.utcoffset(event.datetime())
            except pytz.AmbiguousTimeError:
                event_local = event.datetime() + local_tz.utcoffset(event.datetime(), is_dst=True)

            event_minutes = event_local.hour * 60 + event_local.minute

            event_datetime = datetime.datetime.combine(date, datetime.time(hour=event_local.hour, minute=event_local.minute))
            try:
                if local_tz.dst(event_datetime):  # If currently in daylight saving time
                    standard_time_event_minutes = event_minutes - 60
                    daylight_saving_time_event_minutes = event_minutes
                else:   # If currently in standard time
                    standard_time_event_minutes = event_minutes
                    daylight_saving_time_event_minutes = event_minutes + 60
            except pytz.NonExistentTimeError:
                # Assume that DST is in effect if a NonExistentTimeError occurs
                standard_time_event_minutes = event_minutes - 60
                daylight_saving_time_event_minutes = event_minutes

            return event_minutes, standard_time_event_minutes, daylight_saving_time_event_minutes

        sunrise_minutes, standard_time_sunrise_minutes, daylight_saving_time_sunrise_minutes = handle_sun_event(
            observer, observer.next_rising, current_date, local_tz)
        sunset_minutes, standard_time_sunset_minutes, daylight_saving_time_sunset_minutes = handle_sun_event(
            observer, observer.next_setting, current_date, local_tz)

        if sunset_minutes is not None and sunrise_minutes is not None:
            if sunset_minutes < sunrise_minutes:
                sunset_minutes += 24*60
                if standard_time_sunset_minutes < standard_time_sunrise_minutes:
                    standard_time_sunset_minutes += 24*60
                if daylight_saving_time_sunset_minutes < daylight_saving_time_sunrise_minutes:
                    daylight_saving_time_sunset_minutes += 24*60

        # Ensure the event time never exceeds 24 hours
        if sunrise_minutes:
            sunrise_minutes %= 24*60
            standard_time_sunrise_minutes %= 24*60
            daylight_saving_time_sunrise_minutes %= 24*60
        if sunset_minutes:
            sunset_minutes %= 24*60
            standard_time_sunset_minutes %= 24*60
            daylight_saving_time_sunset_minutes %= 24*60

        # Store the dates and times
        dates.append(current_date)
        sunrise_times.append(sunrise_minutes)
        sunset_times.append(sunset_minutes)
        standard_time_sunrise_times.append(standard_time_sunrise_minutes)
        standard_time_sunset_times.append(standard_time_sunset_minutes)
        daylight_saving_time_sunrise_times.append(daylight_saving_time_sunrise_minutes)
        daylight_saving_time_sunset_times.append(daylight_saving_time_sunset_minutes)
        current_date += datetime.timedelta(days=1)

    # Convert minutes past midnight to a time string
    def minutes_to_time(minutes):
        if minutes is None:
            return ""
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    # Create subplots
    fig = make_subplots(rows=1, cols=3, subplot_titles=(
        'Permanent Standard Time', 'Current Observance', 'Permanent Daylight Saving Time'))

    def add_trace_to_fig(fig, dates, times, name, color, row, col, show_legend=True):
        fig.add_trace(go.Scatter(x=dates, y=times, mode='markers',
                                 name=name,
                                 marker=dict(color=color, size=3),
                                 line=dict(color=color), showlegend=show_legend,
                                 customdata=[name]*len(dates),
                                 hovertemplate='Date: %{x|%Y-%m-%d}<br>Time: %{text}',
                                 text=[minutes_to_time(minutes) for minutes in times]),
                      row=row, col=col)

    # Plot the sunrise and sunset times for permanent standard time
    add_trace_to_fig(fig, dates, standard_time_sunrise_times, 'Sunrise', 'orange', 1, 1)
    add_trace_to_fig(fig, dates, standard_time_sunset_times, 'Sunset', 'blue', 1, 1)

    # Plot the sunrise and sunset times for current time
    add_trace_to_fig(fig, dates, sunrise_times, 'Sunrise', 'orange', 1, 2, show_legend=False)
    add_trace_to_fig(fig, dates, sunset_times, 'Sunset', 'blue', 1, 2, show_legend=False)

    # Plot the sunrise and sunset times for permanent daylight saving time
    add_trace_to_fig(fig, dates, daylight_saving_time_sunrise_times, 'Sunrise', 'orange', 1, 3, show_legend=False)
    add_trace_to_fig(fig, dates, daylight_saving_time_sunset_times, 'Sunset', 'blue', 1, 3, show_legend=False)

    # Define summer and winter solstice dates
    if float(lat) > 0:
        summer_solstice = datetime.date(start_date.year, 6, 20)
        winter_solstice = datetime.date(start_date.year, 12, 21)
    else:
        winter_solstice = datetime.date(start_date.year, 6, 20)
        summer_solstice = datetime.date(start_date.year, 12, 21)

    for column in range(1, 4):
        # Solstice lines
        fig.add_shape(type='line', x0=summer_solstice, y0=0, x1=summer_solstice, y1=24*60,
                      line=dict(color='green', dash='dash'), name='Summer solstice', row=1, col=column)
        fig.add_shape(type='line', x0=winter_solstice, y0=0, x1=winter_solstice, y1=24*60,
                      line=dict(color='blue', dash='dash'), name='Winter solstice', row=1, col=column)

        # Add horizontal lines at 00:00 and 24:00
        fig.add_shape(type='line', x0=dates[0], y0=0, x1=dates[-1], y1=0,
                    line=dict(color='darkgray', width=1), xref='x', yref='y', row=1, col=column)
        fig.add_shape(type='line', x0=dates[0], y0=24*60, x1=dates[-1], y1=24*60,
                    line=dict(color='darkgray', width=1), xref='x', yref='y', row=1, col=column)

        # Add vertical line at January and the end of December
        fig.add_shape(type='line', x0=dates[0], y0=0, x1=dates[0], y1=24*60,
                      line=dict(color='darkgray', width=1), xref='x', yref='y', row=1, col=column)
        fig.add_shape(type='line', x0=dates[-1], y0=0, x1=dates[-1], y1=24*60,
                      line=dict(color='darkgray', width=1), xref='x', yref='y', row=1, col=column)

    # Add annotations for the solstice lines
    fig.add_annotation(
        x=0.45,
        y=-0.1,
        xref='paper',
        yref='paper',
        showarrow=False,
        text="▬ ▬ Summer solstice",
        font=dict(size=12, color='green'),
        align='center',
        xanchor='center',
        yanchor='top',
        standoff=5
    )
    fig.add_annotation(
        x=0.55,
        y=-0.1,
        xref='paper',
        yref='paper',
        showarrow=False,
        text="▬ ▬ Winter solstice",
        font=dict(size=12, color='blue'),
        align='center',
        xanchor='center',
        yanchor='top',
        standoff=5
    )

    # Set the layout properties
    fig.update_layout(
        title={
            'text': 'Sunrise and Sunset Times for ' + title if title else 'Sunrise and Sunset Times',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(
                size=24
            )
        },
        plot_bgcolor='white',
        legend=dict(
            x=0.5,
            y=1.05,
            xanchor='center',
            yanchor='bottom',
            traceorder='normal',
            font=dict(
                family='sans-serif',
                size=12,
            ),
            bgcolor='rgba(0,0,0,0)',
            orientation='h'
        ),
        showlegend=True,
        xaxis=dict(domain=[0, 0.28], anchor='y', matches='x2'),
        xaxis2=dict(domain=[0.36, 0.64], anchor='y2', matches='x3'),
        xaxis3=dict(domain=[0.72, 1], anchor='y3'),
        yaxis=dict(domain=[0, 1], anchor='x', matches='y2'),
        yaxis2=dict(domain=[0, 1], anchor='x2', matches='y3'),
        yaxis3=dict(domain=[0, 1], anchor='x3'),
    )

    # Update all x-axes
    fig.update_xaxes(
        tickformat='%b',
        gridcolor='darkgray',
        dtick='M1'
    )

    # Update all y-axes
    fig.update_yaxes(
        tickvals=[i*60 for i in range(25)],  # 0 to 24 hours, converted to minutes
        ticktext=[f'{i:02d}:00' for i in range(25)],  # 0 to 24 hours, formatted as '00:00'
        tickformat='%H:%M',
        gridcolor='darkgray',
    )

    return fig.to_dict()

if __name__ == '__main__':
    app.run(debug=True, port=5001)

    apex = {'lat': '35.72807100662932', 'lon': '-78.82151304189117', 'title': "Apex, NC"}
    location = apex

    generate_sunrise_sunset_plot(location['lat'], location['lon'], location['title'])