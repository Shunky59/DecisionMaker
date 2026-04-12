import streamlit as st
import random
import string

# --- GLOBAL MEMORY (Our temporary database) ---
# This allows different devices connected to the app to see the same rooms.
@st.cache_resource
def get_rooms():
    return {} # Dictionary to store all active rooms

rooms = get_rooms()

# --- APP SETUP ---
st.set_page_config(page_title="Food Decider", page_icon="🍔")

# --- USER SESSION ---
# This remembers who the user is on their specific phone/browser
if 'room_code' not in st.session_state:
    st.session_state.room_code = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Helper to generate a 4-letter Jackbox-style room code
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

# ==========================================
# PAGE 1: LOGIN / JOIN ROOM
# ==========================================
if st.session_state.room_code is None:
    st.title("🍔 What are we eating?")
    
    # Joining an existing room
    st.write("### Join a Room")
    join_name = st.text_input("Your Name:")
    join_code = st.text_input("Room Code:").upper()
    
    if st.button("Join Room"):
        if join_code in rooms and join_name:
            st.session_state.room_code = join_code
            st.session_state.username = join_name
            # Add user to the room if they aren't already in it
            if join_name not in rooms[join_code]['users']:
                rooms[join_code]['users'].append(join_name)
                rooms[join_code]['votes'][join_name] = {}
            st.rerun()
        else:
            st.error("Invalid Room Code or Name missing.")
            
    st.divider()
    
    # Hosting a new room
    st.write("### Or Host a New Room")
    host_name = st.text_input("Your Name (Host):", key="host")
    if st.button("Create Room"):
        if host_name:
            new_code = generate_code()
            rooms[new_code] = {
                'users': [host_name],
                'votes': {host_name: {}},
                'status': 'voting' # Can be 'voting' or 'results'
            }
            st.session_state.room_code = new_code
            st.session_state.username = host_name
            st.rerun()
        else:
            st.error("Please enter your name first!")

# ==========================================
# PAGE 2: THE ROOM (VOTING & RESULTS)
# ==========================================
else:
    code = st.session_state.room_code
    user = st.session_state.username
    room = rooms[code]
    
    st.title(f"Room: {code}")
    st.write(f"Welcome, **{user}**! Players here: {', '.join(room['users'])}")
    
    # --- THE VOTING PHASE ---
    if room['status'] == 'voting':
        st.write("### Vote on Options!")
        options = ["American 🍔", "Mexican 🌮", "Italian 🍝", "Indian 🍛", "Sushi 🍣"]
        
        with st.form("vote_form"):
            user_votes = {}
            for opt in options:
                user_votes[opt] = st.radio(f"{opt}", ["Yes", "Neutral", "No"], horizontal=True)
            
            submitted = st.form_submit_button("Submit Votes")
            if submitted:
                room['votes'][user] = user_votes
                st.success("Votes submitted! Waiting for others...")
        
        st.divider()
        # Because we aren't using a live database yet, users need to click a button to refresh the screen
        if st.button("Refresh / Check who voted"):
            st.rerun()
            
        if st.button("Everyone has voted! Show Results"):
            room['status'] = 'results'
            st.rerun()

    # --- THE RESULTS PHASE ---
    elif room['status'] == 'results':
        st.write("### 🥁 And the results are in...")
        
        # Tally the votes
        options = ["American 🍔", "Mexican 🌮", "Italian 🍝", "Indian 🍛", "Sushi 🍣"]
        yes_counts = {opt: 0 for opt in options}
        total_players = len(room['users'])
        
        for player, votes in room['votes'].items():
            for opt, vote in votes.items():
                if vote == "Yes":
                    yes_counts[opt] += 1
                    
        # Find unanimous Yes votes
        unanimous = [opt for opt, count in yes_counts.items() if count == total_players and total_players > 0]
        
        # Logic 1: Single Unanimous Winner
        if len(unanimous) == 1:
            st.success(f"### 🎉 Unanimous Winner: {unanimous[0]}!")
            
        # Logic 2: Multiple Unanimous Winners (The Wheel)
        elif len(unanimous) > 1:
            st.warning(f"### 🤝 Multiple Unanimous Choices: {', '.join(unanimous)}")
            st.info("Spinning the random wheel...")
            winner = random.choice(unanimous)
            st.success(f"### 🎡 The Wheel Chose: {winner}!")
            
        # Logic 3: No Unanimous Winner (The Compromise)
        else:
            st.error("### 🤷 No Unanimous Winner. Best Compromises:")
            # Sort options by whoever got the most 'Yes' votes
            sorted_opts = sorted(yes_counts.items(), key=lambda x: x[1], reverse=True)
            for opt, count in sorted_opts:
                if count > 0:
                    st.write(f"**{opt}**: {count} 'Yes' votes")
                    
        if st.button("Back to Voting"):
            room['status'] = 'voting'
            st.rerun()
