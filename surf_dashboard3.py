import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import math

# Page configuration
st.set_page_config(
    page_title="San Diego Surf Dashboard",
    page_icon="🏄‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced San Diego surf spots with detailed characteristics
SD_SURF_SPOTS = {
    'Ocean Beach': {
        'lat': 32.7533, 'lon': -117.2564,
        'break_type': 'Beach Break',
        'skill_level': 'Medium',
        'ideal_boards': ['Shortboard', 'Funboard'],
        'description': 'Powerful beach break with consistent waves',
        'tide_station': '9410170'
    },
    'Mission Beach': {
        'lat': 32.7767, 'lon': -117.2533,
        'break_type': 'Beach Break',
        'skill_level': 'Low',
        'ideal_boards': ['Longboard', 'Funboard'],
        'description': 'Gentle beach break, great for beginners',
        'tide_station': '9410170'
    },
    'Pacific Beach': {
        'lat': 32.7964, 'lon': -117.2581,
        'break_type': 'Beach Break',
        'skill_level': 'Medium',
        'ideal_boards': ['Shortboard', 'Funboard'],
        'description': 'Popular beach break with varied conditions',
        'tide_station': '9410170'
    },
    'La Jolla Shores': {
        'lat': 32.8328, 'lon': -117.2713,
        'break_type': 'Beach Break',
        'skill_level': 'Low',
        'ideal_boards': ['Longboard', 'SUP'],
        'description': 'Protected cove, perfect for learning',
        'tide_station': '9410230'
    },
    'Blacks Beach': {
        'lat': 32.8894, 'lon': -117.2519,
        'break_type': 'Beach Break',
        'skill_level': 'High',
        'ideal_boards': ['Shortboard', 'Gun'],
        'description': 'Powerful waves, advanced surfers only',
        'tide_station': '9410230'
    },
    'Swamis': {
        'lat': 33.0364, 'lon': -117.2956,
        'break_type': 'Point Break',
        'skill_level': 'Medium',
        'ideal_boards': ['Longboard', 'Funboard'],
        'description': 'Classic point break with long rides',
        'tide_station': '9410580'
    },
    'Cardiff Reef': {
        'lat': 33.0139, 'lon': -117.2806,
        'break_type': 'Reef Break',
        'skill_level': 'High',
        'ideal_boards': ['Shortboard', 'Funboard'],
        'description': 'Consistent reef break with quality waves',
        'tide_station': '9410580'
    }
}

class FixedSurfDashboard:
    def __init__(self):
        self.marine_api_url = "https://marine-api.open-meteo.com/v1/marine"
        self.weather_api_url = "https://api.open-meteo.com/v1/forecast"
        self.noaa_tides_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_marine_data(_self, lat, lon):
        """Get marine data using correct Marine API parameters"""
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': [
                    'wave_height', 'wave_direction', 'wave_period',
                    'wind_wave_height', 'swell_wave_height', 'swell_wave_direction',
                    'swell_wave_period'
                ],
                'daily': [
                    'wave_height_max', 'wave_direction_dominant', 
                    'wave_period_max'
                ],
                'timezone': 'America/Los_Angeles',
                'forecast_days': 7
            }
            
            response = requests.get(_self.marine_api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Marine API Error {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"Error fetching marine data: {e}")
        return None
    
    @st.cache_data(ttl=300)
    def get_weather_data(_self, lat, lon):
        """Get weather data (including wind) using Weather API"""
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': [
                    'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m'
                ],
                'daily': [
                    'wind_speed_10m_max', 'wind_direction_10m_dominant'
                ],
                'timezone': 'America/Los_Angeles',
                'forecast_days': 7
            }
            
            response = requests.get(_self.weather_api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            st.error(f"Error fetching weather data: {e}")
        return None
    
    @st.cache_data(ttl=1800)  # Cache tide data for 30 minutes
    def get_tide_data(_self, station_id):
        """Get tide predictions from NOAA"""
        try:
            today = datetime.now()
            end_date = today + timedelta(days=2)
            
            params = {
                'station': station_id,
                'product': 'predictions',
                'begin_date': today.strftime('%Y%m%d'),
                'end_date': end_date.strftime('%Y%m%d'),
                'datum': 'MLLW',
                'units': 'english',
                'time_zone': 'lst_ldt',
                'format': 'json'
            }
            
            response = requests.get(_self.noaa_tides_url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.warning(f"Tide data unavailable: {e}")
        return None
    
    def combine_marine_weather_data(self, marine_data, weather_data):
        """Combine marine and weather data into one structure"""
        if not marine_data:
            return None
            
        combined_data = marine_data.copy()
        
        # Add weather data to marine data
        if weather_data and 'hourly' in weather_data:
            if 'hourly' not in combined_data:
                combined_data['hourly'] = {}
            
            # Add wind data from weather API
            for key in ['wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m']:
                if key in weather_data['hourly']:
                    combined_data['hourly'][key] = weather_data['hourly'][key]
        
        return combined_data
    
    def create_wave_height_heatmap(self, spots_data):
        """Create wave height heatmap across spots and time"""
        if not spots_data:
            return None
            
        # Prepare data for heatmap
        data_matrix = []
        spot_names = []
        time_labels = []
        
        # Get time labels from first valid dataset
        for spot_name, data in spots_data.items():
            if data and 'hourly' in data and 'time' in data['hourly']:
                time_labels = [datetime.fromisoformat(t.replace('T', ' ')).strftime('%H:%M') 
                              for t in data['hourly']['time'][:24]]
                break
        
        if not time_labels:
            return None
        
        # Collect wave height data for each spot
        for spot_name, data in spots_data.items():
            if data and 'hourly' in data and 'wave_height' in data['hourly']:
                wave_heights = data['hourly']['wave_height'][:24]
                # Pad with zeros if data is shorter than 24 hours
                while len(wave_heights) < 24:
                    wave_heights.append(0)
                data_matrix.append(wave_heights[:24])
                spot_names.append(spot_name)
        
        if not data_matrix:
            return None
        
        # Create heatmap
        fig = px.imshow(
            data_matrix,
            x=time_labels,
            y=spot_names,
            color_continuous_scale='Blues',
            labels={'color': 'Wave Height (ft)'},
            title='24-Hour Wave Height Forecast Heatmap',
            aspect='auto'
        )
        
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Surf Spots",
            height=400
        )
        
        return fig
    
    def create_wind_rose_diagram(self, combined_data):
        """Create wind rose diagram"""
        if not combined_data or 'hourly' not in combined_data:
            return None
        
        if 'wind_direction_10m' not in combined_data['hourly'] or 'wind_speed_10m' not in combined_data['hourly']:
            return None
            
        wind_directions = combined_data['hourly']['wind_direction_10m'][:24]
        wind_speeds = combined_data['hourly']['wind_speed_10m'][:24]
        
        # Filter out None values
        valid_data = [(d, s) for d, s in zip(wind_directions, wind_speeds) if d is not None and s is not None]
        
        if not valid_data:
            return None
        
        directions, speeds = zip(*valid_data)
        
        fig = go.Figure()
        
        # Create wind rose
        fig.add_trace(go.Scatterpolar(
            r=speeds,
            theta=directions,
            mode='markers',
            marker=dict(
                color=speeds,
                colorscale='Viridis',
                size=8,
                colorbar=dict(title="Wind Speed (mph)")
            ),
            name='Wind Data'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(speeds) + 5]),
                angularaxis=dict(
                    tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                    ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                )
            ),
            title="24-Hour Wind Rose Diagram",
            height=400
        )
        
        return fig
    
    def create_tide_chart(self, tide_data):
        """Create tide chart overlay"""
        if not tide_data or 'predictions' not in tide_data:
            return None
            
        predictions = tide_data['predictions']
        times = []
        heights = []
        
        for p in predictions:
            try:
                times.append(datetime.strptime(p['t'], '%Y-%m-%d %H:%M'))
                heights.append(float(p['v']))
            except (ValueError, KeyError):
                continue
        
        if not times:
            return None
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=times,
            y=heights,
            mode='lines',
            fill='tonexty',
            line=dict(color='lightblue', width=2),
            name='Tide Height'
        ))
        
        fig.update_layout(
            title="48-Hour Tide Forecast",
            xaxis_title="Time",
            yaxis_title="Tide Height (ft)",
            height=300,
            showlegend=False
        )
        
        return fig
    
    def calculate_surf_score(self, combined_data, user_prefs):
        """Calculate surf score based on user preferences"""
        if not combined_data or 'hourly' not in combined_data:
            return 0
        
        try:
            current_wave_height = combined_data['hourly']['wave_height'][0]
            current_wind_speed = combined_data['hourly'].get('wind_speed_10m', [None])[0]
            
            score = 0
            
            # Wave height scoring based on skill level
            if user_prefs['skill_level'] == 'Low':
                if 1 <= current_wave_height <= 3:
                    score += 40
                elif current_wave_height < 1:
                    score += 20
            elif user_prefs['skill_level'] == 'Medium':
                if 2 <= current_wave_height <= 6:
                    score += 40
                elif 1 <= current_wave_height < 2:
                    score += 25
            else:  # High skill
                if current_wave_height >= 4:
                    score += 40
                elif 2 <= current_wave_height < 4:
                    score += 30
            
            # Wind scoring (if available)
            if current_wind_speed is not None:
                if current_wind_speed < 10:
                    score += 30
                elif current_wind_speed < 15:
                    score += 20
                else:
                    score += 5
            else:
                score += 15  # Neutral score if no wind data
            
            # Board type bonus
            score += 10  # Base bonus for any conditions
            
            return min(score, 100)
            
        except (KeyError, IndexError, TypeError):
            return 0
    
    def recommend_surf_spots(self, user_prefs, spots_data):
        """Recommend surf spots based on user preferences"""
        recommendations = []
        
        for spot_name, spot_info in SD_SURF_SPOTS.items():
            combined_data = spots_data.get(spot_name)
            
            # Check if break type matches preference
            break_match = (user_prefs['break_type'] == 'Any' or 
                          spot_info['break_type'] == user_prefs['break_type'])
            
            # Check if board type is suitable
            board_match = (user_prefs['board_length'] in spot_info['ideal_boards'])
            
            # Calculate surf score
            surf_score = self.calculate_surf_score(combined_data, user_prefs)
            
            # Skill level matching
            skill_match = (user_prefs['skill_level'] == spot_info['skill_level'])
            
            # Calculate overall recommendation score
            rec_score = surf_score
            if break_match:
                rec_score += 20
            if board_match:
                rec_score += 15
            if skill_match:
                rec_score += 25
            
            recommendations.append({
                'spot': spot_name,
                'score': rec_score,
                'surf_score': surf_score,
                'break_type': spot_info['break_type'],
                'skill_level': spot_info['skill_level'],
                'description': spot_info['description'],
                'break_match': break_match,
                'board_match': board_match,
                'skill_match': skill_match
            })
        
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)
    
    def create_dashboard(self):
        """Create the enhanced Streamlit dashboard"""
        st.title("🏄‍♂️ San Diego Surf Dashboard")
        st.markdown("Real-time surf forecasts with personalized recommendations")
        
        # Sidebar for user preferences and controls
        with st.sidebar:
            st.header("🎯 Surf Preferences")
            
            # User preference inputs
            skill_level = st.selectbox(
                "Skill Level",
                ['Low', 'Medium', 'High'],
                index=1
            )
            
            board_length = st.selectbox(
                "Preferred Board",
                ['Longboard', 'Funboard', 'Shortboard', 'SUP', 'Gun'],
                index=1
            )
            
            break_type = st.selectbox(
                "Preferred Break Type",
                ['Any', 'Beach Break', 'Point Break', 'Reef Break'],
                index=0
            )
            
            user_prefs = {
                'skill_level': skill_level,
                'board_length': board_length,
                'break_type': break_type
            }
            
            st.divider()
            
            # Controls
            st.header("⚙️ Controls")
            selected_spots = st.multiselect(
                "Select Surf Spots",
                list(SD_SURF_SPOTS.keys()),
                default=list(SD_SURF_SPOTS.keys())[:4]
            )
            
            refresh_button = st.button("🔄 Refresh All Data", type="primary")
        
        # Main content area
        if refresh_button or 'surf_data' not in st.session_state:
            with st.spinner("🌊 Fetching surf data..."):
                spots_data = {}
                progress_bar = st.progress(0)
                
                for i, spot_name in enumerate(selected_spots):
                    spot_info = SD_SURF_SPOTS[spot_name]
                    
                    # Get marine and weather data separately
                    marine_data = self.get_marine_data(spot_info['lat'], spot_info['lon'])
                    weather_data = self.get_weather_data(spot_info['lat'], spot_info['lon'])
                    
                    # Combine the data
                    combined_data = self.combine_marine_weather_data(marine_data, weather_data)
                    spots_data[spot_name] = combined_data
                    
                    progress_bar.progress((i + 1) / len(selected_spots))
                
                st.session_state.surf_data = spots_data
                progress_bar.empty()
        
        if 'surf_data' in st.session_state:
            spots_data = st.session_state.surf_data
            
            # Personalized Recommendations Section
            st.header("🎯 Personalized Surf Spot Recommendations")
            recommendations = self.recommend_surf_spots(user_prefs, spots_data)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                for i, rec in enumerate(recommendations[:3]):
                    score_color = "🟢" if rec['score'] >= 80 else "🟡" if rec['score'] >= 60 else "🔴"
                    
                    with st.expander(f"{score_color} #{i+1}: {rec['spot']} (Score: {rec['score']:.0f}/100)", expanded=i==0):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**Break Type:** {rec['break_type']}")
                            st.write(f"**Skill Level:** {rec['skill_level']}")
                            st.write(f"**Current Surf Score:** {rec['surf_score']:.0f}/100")
                        with col_b:
                            st.write(f"**Break Match:** {'✅' if rec['break_match'] else '❌'}")
                            st.write(f"**Board Match:** {'✅' if rec['board_match'] else '❌'}")
                            st.write(f"**Skill Match:** {'✅' if rec['skill_match'] else '❌'}")
                        st.write(f"*{rec['description']}*")
            
            with col2:
                # Quick stats
                st.metric("Top Recommendation", recommendations[0]['spot'])
                st.metric("Best Score", f"{recommendations[0]['score']:.0f}/100")
                
                # Preference summary
                st.subheader("Your Preferences")
                st.write(f"🏄‍♂️ Skill: {skill_level}")
                st.write(f"🏄 Board: {board_length}")
                st.write(f"🌊 Break: {break_type}")
            
            st.divider()
            
            # Enhanced Visualizations
            st.header("📊 Advanced Surf Analytics")
            
            viz_tabs = st.tabs(["🗺️ Wave Heatmap", "💨 Wind Analysis", "🌊 Tide Charts"])
            
            with viz_tabs[0]:
                st.subheader("24-Hour Wave Height Heatmap")
                heatmap_fig = self.create_wave_height_heatmap(spots_data)
                if heatmap_fig:
                    st.plotly_chart(heatmap_fig, use_container_width=True)
                else:
                    st.warning("Unable to generate heatmap - checking data...")
                    # Show debug info
                    for spot, data in spots_data.items():
                        if data and 'hourly' in data:
                            st.write(f"✅ {spot}: Data available")
                        else:
                            st.write(f"❌ {spot}: No data")
            
            with viz_tabs[1]:
                st.subheader("Wind Rose Diagram")
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_wind_spot = st.selectbox("Select spot for wind analysis:", selected_spots)
                    if selected_wind_spot and spots_data.get(selected_wind_spot):
                        wind_fig = self.create_wind_rose_diagram(spots_data[selected_wind_spot])
                        if wind_fig:
                            st.plotly_chart(wind_fig, use_container_width=True)
                        else:
                            st.warning("Wind data not available for this spot")
                
                with col2:
                    # Wind conditions summary
                    if selected_wind_spot and spots_data.get(selected_wind_spot):
                        combined_data = spots_data[selected_wind_spot]
                        if combined_data and 'hourly' in combined_data:
                            wind_speed = combined_data['hourly'].get('wind_speed_10m', [None])[0]
                            wind_dir = combined_data['hourly'].get('wind_direction_10m', [None])[0]
                            
                            if wind_speed is not None:
                                st.metric("Current Wind Speed", f"{wind_speed:.1f} mph")
                            if wind_dir is not None:
                                st.metric("Wind Direction", f"{wind_dir:.0f}°")
                            
                            # Wind quality assessment
                            if wind_speed is not None:
                                if wind_speed < 10:
                                    wind_quality = "🟢 Excellent (Light)"
                                elif wind_speed < 15:
                                    wind_quality = "🟡 Good (Moderate)"
                                else:
                                    wind_quality = "🔴 Poor (Strong)"
                                
                                st.write(f"**Wind Quality:** {wind_quality}")
            
            with viz_tabs[2]:
                st.subheader("Tide Forecasts")
                tide_spot = st.selectbox("Select spot for tide data:", selected_spots)
                
                if tide_spot:
                    spot_info = SD_SURF_SPOTS[tide_spot]
                    tide_data = self.get_tide_data(spot_info['tide_station'])
                    
                    if tide_data:
                        tide_fig = self.create_tide_chart(tide_data)
                        if tide_fig:
                            st.plotly_chart(tide_fig, use_container_width=True)
                        else:
                            st.warning("Unable to parse tide data")
                    else:
                        st.warning("Tide data temporarily unavailable")
            
            st.divider()
            
            # Current Conditions (Enhanced)
            st.header("🌊 Current Surf Conditions")
            
            condition_cols = st.columns(len(selected_spots))
            
            for i, spot_name in enumerate(selected_spots):
                with condition_cols[i]:
                    st.subheader(spot_name)
                    
                    combined_data = spots_data.get(spot_name)
                    if combined_data and 'hourly' in combined_data:
                        try:
                            # Current conditions
                            wave_height = combined_data['hourly']['wave_height'][0]
                            wave_period = combined_data['hourly'].get('wave_period', [None])[0]
                            wind_speed = combined_data['hourly'].get('wind_speed_10m', [None])[0]
                            wind_direction = combined_data['hourly'].get('wind_direction_10m', [None])[0]
                            
                            # Display metrics
                            st.metric("Wave Height", f"{wave_height:.1f} ft")
                            
                            if wave_period is not None:
                                st.metric("Period", f"{wave_period:.0f} sec")
                            
                            if wind_speed is not None and wind_direction is not None:
                                st.metric("Wind", f"{wind_speed:.0f} mph @ {wind_direction:.0f}°")
                            elif wind_speed is not None:
                                st.metric("Wind Speed", f"{wind_speed:.0f} mph")
                            
                            # Quick surf score
                            score = self.calculate_surf_score(combined_data, user_prefs)
                            score_emoji = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"
                            st.metric("Surf Score", f"{score_emoji} {score:.0f}/100")
                            
                        except (KeyError, IndexError, TypeError) as e:
                            st.error(f"Error parsing data: {e}")
                    else:
                        st.error("Data unavailable")
            
            # Footer with data sources
            st.divider()
            st.markdown("""
            **Data Sources:**
            - Marine Forecasts: Open-Meteo Marine API
            - Weather Data: Open-Meteo Weather API  
            - Tide Data: NOAA CO-OPS API
            """)

def main():
    dashboard = FixedSurfDashboard()
    dashboard.create_dashboard()

if __name__ == "__main__":
    main()