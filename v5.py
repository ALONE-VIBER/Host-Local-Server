import socket
from flask import Flask, render_template_string, request, redirect, url_for, session

# Initialize Flask app
app = Flask(__name__)

# Set a secret key for session management
app.secret_key = 'your_secret_key'  # You can change this to any random string

# Function to get the local IP address of the laptop to access from phone
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # Doesn't need to be reachable
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

# Game state (board, current turn, nickname)
def initialize_game():
    return {
        "board": ['' for _ in range(9)],  # 9 empty cells
        "current_turn": 'X',  # X starts first
        "game_over": False,
        "result": "",
        "nickname": "",  # Store the user's nickname
    }

# Function to check for a win condition
def check_win(game_state):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]              # Diagonals
    ]
    
    for condition in win_conditions:
        if game_state["board"][condition[0]] == game_state["board"][condition[1]] == game_state["board"][condition[2]] and game_state["board"][condition[0]] != '':
            game_state["game_over"] = True
            game_state["result"] = f"{game_state['board'][condition[0]]} wins!"
            return

    # Check if it's a draw (board is full)
    if '' not in game_state["board"]:
        game_state["game_over"] = True
        game_state["result"] = "It's a draw!"

# Route to start the game and set the nickname
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['nickname'] = request.form['nickname']
        session['game_state'] = initialize_game()  # Initialize game state for this session
        return render_template_string(mode_selection_html)
    return render_template_string(nickname_form_html)

# Route to choose the game mode (Single Player or Multiplayer)
@app.route("/mode/<mode>", methods=["GET", "POST"])
def select_mode(mode):
    if mode == 'multiplayer' and request.method == 'POST':
        room_code = request.form['room_code']
        session['room_code'] = room_code
        return redirect(url_for('game'))
    
    session['mode'] = mode
    if mode == 'multiplayer':
        return render_template_string(room_code_input_html)
    return redirect(url_for('game'))

# Route for waiting for opponent in multiplayer
@app.route("/waiting", methods=["GET"])
def waiting_for_opponent():
    return render_template_string(waiting_html, room_code=session['room_code'])

# Route for the actual game
@app.route("/game", methods=["GET"])
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))  # Redirect to nickname input if not set
    
    game_state = session.get('game_state', initialize_game())
    # Here you can add your game logic and updates
    return render_template_string(game_html, game_state=game_state)

# HTML for nickname form
nickname_form_html = """
    <h1>Enter your nickname</h1>
    <form method="POST">
        <input type="text" name="nickname" required>
        <button type="submit">Submit</button>
    </form>
"""

# HTML for mode selection
mode_selection_html = """
    <h1>Welcome, {{ session['nickname'] }}!</h1>
    <h2>Select Game Mode</h2>
    <form method="POST" action="{{ url_for('select_mode', mode='singleplayer') }}">
        <button type="submit">Single Player</button>
    </form>
    <form method="POST" action="{{ url_for('select_mode', mode='multiplayer') }}">
        <button type="submit">Multiplayer</button>
    </form>
"""

# HTML for room code input (for multiplayer mode)
room_code_input_html = """
    <h1>Enter Room Code</h1>
    <form method="POST">
        <input type="text" name="room_code" required>
        <button type="submit">Enter Room</button>
    </form>
"""

# HTML for waiting for an opponent
waiting_html = """
    <h1>Waiting for opponent to join...</h1>
    <p>Room Code: {{ session['room_code'] }}</p>
"""

# HTML for the game board
game_html = """
    <h1>Tic-Tac-Toe Game</h1>
    <h2>Player: {{ session['nickname'] }} - {{ game_state['current_turn'] }}'s turn</h2>
    <div id="board">
        <div class="row">
            <button onclick="makeMove(0)">{{ game_state['board'][0] }}</button>
            <button onclick="makeMove(1)">{{ game_state['board'][1] }}</button>
            <button onclick="makeMove(2)">{{ game_state['board'][2] }}</button>
        </div>
        <div class="row">
            <button onclick="makeMove(3)">{{ game_state['board'][3] }}</button>
            <button onclick="makeMove(4)">{{ game_state['board'][4] }}</button>
            <button onclick="makeMove(5)">{{ game_state['board'][5] }}</button>
        </div>
        <div class="row">
            <button onclick="makeMove(6)">{{ game_state['board'][6] }}</button>
            <button onclick="makeMove(7)">{{ game_state['board'][7] }}</button>
            <button onclick="makeMove(8)">{{ game_state['board'][8] }}</button>
        </div>
    </div>
    <script>
        function makeMove(index) {
            // Add the JavaScript to handle moves
            fetch('/make_move', {method: 'POST', body: JSON.stringify({index: index})});
        }
    </script>
"""

if __name__ == "__main__":
    # Get the IP address to make it accessible in the local network
    ip_address = get_ip()
    print(f"Running on {ip_address}:5000 (accessible on the same Wi-Fi network)")
    
    # Run the app, making it accessible on the local network (use 0.0.0.0 for external access)
    app.run(host=ip_address, port=5000, debug=True)
