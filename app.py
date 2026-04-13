import streamlit as st
import random
import string
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- GLOBAL MEMORY (For live rooms) ---
@st.cache_resource
def get_rooms():
    return {}

rooms = get_rooms()

# --- LIVE DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
# REPLACE THIS WITH YOUR ACTUAL GOOGLE SHEET URL!
SHEET_URL = "https://docs.google.com/spreadsheets/d/1j0JQbMA-tu4eKmUqpdV49P1l1qs_U-S679vW3YR_ypQ/edit?gid=0#gid=0" 

def get_saved_lists():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", usecols=[0, 1])
        df = df.dropna(subset=['ListName']) 
        
        db_lists = {}
        for index, row in df.iterrows():
            list_name = row['ListName']
            options = [opt.strip() for opt in str(row['OptionsString']).split(",")]
            db_lists[list_name] = options
        return db_lists, df
    except Exception as e:
        return {}, pd.DataFrame(columns=['ListName', 'OptionsString'])

saved_lists, db_dataframe = get_saved_lists()

# --- PRE-MADE CATEGORIES ---
PREMADE_CATS = {
    "Food (Specific)": ["Burgers 🍔", "Pizza 🍕", "Pasta 🍝", "Sushi 🍣", "Tacos 🌮", "Ramen 🍜", "Curry 🍛"],
    "Food (Broad)": ["American", "Mexican", "Italian", "Asian", "Indian", "Mediterranean"],
    "Movie Genres": ["Action 💥", "Comedy 😂", "Horror 👻", "Sci-Fi 👽", "Romance ❤️"],
    "Date Night": ["Board Games 🎲", "Movie Theater 🍿", "Cook a Meal 🍳", "Mini Golf ⛳"]
}

# --- APP SETUP ---
st.set_page_config(page_title="Decision Maker", page_icon="🎯")

for key in ['room_code', 'username', 'has_voted']:
    if key not in st.session_state:
        st.session_state[key] = None

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

# ==========================================
# PAGE 1: LOGIN / HOST ROOM
# ==========================================
if st.session_state.room_code is None:
    st.title("🎯 The Ultimate Decision Maker")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Join a Room")
        join_name = st.text_input("Your Name:")
        join_code = st.text_input("Room Code:").upper()
        
        if st.button("Join Room"):
            if join_code in rooms and join_name:
                st.session_state.room_code = join_code
                st.session_state.username = join_name
                st.session_state.has_voted = False
                if join_name not in rooms[join_code]['users']:
                    rooms[join_code]['users'].append(join_name)
                    rooms[join_code]['votes'][join_name] = {}
                st.rerun()
            else:
                st.error("Invalid Code or Name.")
                
    with col2:
        st.write("### Host a New Room")
        host_name = st.text_input("Your Name (Host):")
        decision_type = st.radio("What are we deciding on?", 
                                 ["Use Pre-made", "Paste Custom List", "Load Saved List"])
        
        selected_options = []
        save_list = False
        list_name = ""
        
        if decision_type == "Use Pre-made":
            cat = st.selectbox("Choose Category:", list(PREMADE_CATS.keys()))
            selected_options = PREMADE_CATS[cat]
            
        elif decision_type == "Paste Custom List":
            custom_text = st.text_input("Paste options (separated by commas):")
            if custom_text:
                selected_options = [opt.strip() for opt in custom_text.split(",") if opt.strip()]
            
            save_list = st.checkbox("Save this list to database?")
            if save_list:
                list_name = st.text_input("Name for this list:")

        elif decision_type == "Load Saved List":
            if saved_lists:
                loaded_name = st.selectbox("Choose a saved list:", list(saved_lists.keys()))
                selected_options = saved_lists[loaded_name]
            else:
                st.warning("No saved lists found in Google Sheets yet!")
                
        if st.button("Create Room"):
            if host_name and selected_options:
                
                if decision_type == "Paste Custom List" and save_list and list_name:
                    if list_name not in saved_lists:
                        options_string = ", ".join(selected_options)
                        new_row = pd.DataFrame([{'ListName': list_name, 'OptionsString': options_string}])
                        updated_df = pd.concat([db_dataframe, new_row], ignore_index=True)
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
                        st.cache_data.clear() 

                new_code = generate_code()
                rooms[new_code] = {
                    'users': [host_name],
                    'votes': {host_name: {}},
                    'status': 'voting',
                    'options': selected_options,
                    'host': host_name,
                    'wheel_winner': None # Track the wheel spin!
                }
                st.session_state.room_code = new_code
                st.session_state.username = host_name
                st.session_state.has_voted = False
                st.rerun()
            else:
                st.error("Please enter your name and ensure you have options selected.")

# ==========================================
# PAGE 2: THE ROOM (VOTING & RESULTS)
# ==========================================
else:
    code = st.session_state.room_code
    user = st.session_state.username
    room = rooms[code]
    
    st.title(f"Room: {code}")
    st.write(f"Players here: {', '.join(room['users'])}")
    
    if room['status'] == 'voting':
        st.write("### Vote on Options")
        
        if not st.session_state.has_voted:
            with st.form("vote_form"):
                user_votes = {}
                for opt in room['options']:
                    user_votes[opt] = st.radio(f"**{opt}**", ["Yes", "Neutral", "No"], horizontal=True)
                
                if st.form_submit_button("Submit Votes"):
                    # FEATURE 1: Prevent voting all exactly the same
                    if len(room['options']) > 1 and len(set(user_votes.values())) == 1:
                        st.error("🚫 You must have an opinion! You cannot vote exactly the same for every single option.")
                    else:
                        room['votes'][user] = user_votes
                        st.session_state.has_voted = True
                        st.rerun()
        else:
            st.success("✅ Your votes are locked in! Waiting for others...")
            colA, colB = st.columns(2)
            with colA:
                if st.button("Edit My Votes"):
                    st.session_state.has_voted = False
                    st.rerun()
            with colB:
                if st.button("🔄 Sync Screen"):
                    st.rerun()
                    
        st.divider()
        if user == room['host']:
            st.write("👑 **Host Controls**")
            if st.button("Everyone voted! Reveal Results"):
                room['status'] = 'results'
                st.rerun()

    elif room['status'] == 'results':
        st.write("### 🥁 The Results Are In...")
        
        yes_counts = {opt: 0 for opt in room['options']}
        total_players = len(room['users'])
        
        for player, votes in room['votes'].items():
            for opt, vote in votes.items():
                if vote == "Yes":
                    yes_counts[opt] += 1
                    
        unanimous = [opt for opt, count in yes_counts.items() if count == total_players and total_players > 0]
        
        if len(unanimous) == 1:
            st.success(f"### 🎉 Unanimous Winner: {unanimous[0]}!")
            
        elif len(unanimous) > 1:
            st.warning(f"### 🤝 Multiple Unanimous Choices: {', '.join(unanimous)}")
            
            # FEATURE 3: Interactive Wheel Spin
            if room['wheel_winner']:
                st.success(f"### 🎡 The Wheel Chose: {room['wheel_winner']}!")
            else:
                if user == room['host']:
                    if st.button("🎡 Spin the Wheel!"):
                        room['wheel_winner'] = random.choice(unanimous)
                        st.rerun()
                else:
                    st.info("Waiting for the Host to spin the wheel...")
                    if st.button("🔄 Check Wheel Status"):
                        st.rerun()
        else:
            st.error("### 🤷 No Unanimous Winner. Best Compromises:")
            sorted_opts = sorted(yes_counts.items(), key=lambda x: x[1], reverse=True)
            
            has_compromises = False
            for opt, count in sorted_opts:
                if count > 0:
                    st.write(f"**{opt}**: {count} 'Yes' votes")
                    has_compromises = True
            
            # FEATURE 2: Handle no 'Yes' votes gracefully
            if not has_compromises:
                st.warning("Actually... there are no compromises. Nobody voted 'Yes' for anything! 😭")
                    
        st.divider()
        if user == room['host']:
            if st.button("Back to Voting / Restart"):
                room['status'] = 'voting'
                room['wheel_winner'] = None # Reset the wheel
                for p in room['votes']:
                    room['votes'][p] = {}
                st.rerun()
