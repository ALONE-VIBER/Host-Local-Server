import time
import threading
import socket
import random
from flask import Flask, render_template_string, request, redirect, url_for, session

# Initialize Flask app
app = Flask(__name__)

# Set a secret key for session management
app.secret_key = 'your_secret_key'

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

# Function to initialize a game for single or multiplayer
def initialize_game():
    return {
        "board": ['' for _ in range(9)],  # 9 empty cells
        "current_turn": '',  # Set later to X or O
        "game_over": False,
        "result": "",
        "nickname": "",  # Store the user's nickname
        "player_x": '',  # To store who is X
        "player_o": ''   # To store who is O
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
        return redirect(url_for('choose_mode'))
    return render_template_string(nickname_form_html)

# Route to choose between Single Player and Multiplayer
@app.route("/choose_mode", methods=["GET"])
def choose_mode():
    return render_template_string(mode_choice_html)

# Route to start single player game
@app.route("/single_player", methods=["GET"])
def single_player():
    game_state = session.get('game_state', initialize_game())
    game_state["current_turn"] = 'X'  # Single Player, X starts
    session['game_state'] = game_state
    return redirect(url_for('game'))

# Route to start multiplayer game
@app.route("/multiplayer", methods=["GET"])
def multiplayer():
    game_state = session.get('game_state', initialize_game())
    
    # Randomly assign X and O
    game_state["player_x"] = session['nickname']
    game_state["player_o"] = f"Player{random.randint(1000, 9999)}"
    game_state["current_turn"] = 'X'  # Player X always starts first
    
    session['game_state'] = game_state
    return redirect(url_for('game'))

@app.route("/game", methods=["GET"])
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))  # Redirect to nickname input if not set
    
    game_state = session.get('game_state', initialize_game())
    
    return render_template_string(game_html, 
                                  board=game_state["board"], 
                                  current_turn=game_state["current_turn"], 
                                  game_over=game_state["game_over"], 
                                  result=game_state["result"], 
                                  nickname=session['nickname'], 
                                  player_x=game_state["player_x"], 
                                  player_o=game_state["player_o"])

@app.route("/move/<int:cell>", methods=["GET"])
def move(cell):
    game_state = session.get('game_state', initialize_game())

    if game_state["game_over"] or game_state["board"][cell] != '':
        return redirect(url_for('game'))

    if game_state["current_turn"] == 'X' and game_state["nickname"] == game_state["player_x"]:
        game_state["board"][cell] = 'X'
        check_win(game_state)
        if not game_state["game_over"]:
            game_state["current_turn"] = 'O'
    elif game_state["current_turn"] == 'O' and game_state["nickname"] == game_state["player_o"]:
        game_state["board"][cell] = 'O'
        check_win(game_state)
        if not game_state["game_over"]:
            game_state["current_turn"] = 'X'

    session['game_state'] = game_state
    return redirect(url_for('game'))

@app.route("/restart", methods=["GET"])
def restart():
    if 'nickname' not in session:
        return redirect(url_for('index'))

    session['game_state'] = initialize_game()  # Reset the game state
    return redirect(url_for('choose_mode'))  # Redirect to mode selection after restart

@app.before_request
def log_access():
    print(f"🌐 Access from: {request.remote_addr}")

# HTML template for the nickname form
nickname_form_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enter Nickname</title>
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 50px; }
        input[type="text"] { padding: 10px; font-size: 1em; }
        .submit-btn { padding: 10px 20px; font-size: 1em; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .submit-btn:hover { background-color: #45a049; }
    </style>
</head>
<body>

<h1>Enter Your Nickname</h1>
<form method="POST" action="/">
    <input type="text" name="nickname" placeholder="Enter Nickname" required>
    <br><br>
    <button class="submit-btn" type="submit">Start Game</button>
</form>

</body>
</html>
"""

# HTML template for the game mode choice (Single Player / Multiplayer)
mode_choice_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Choose Game Mode</title>
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 50px; }
        button { padding: 10px 20px; font-size: 1.5em; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
    </style>
</head>
<body>

<h1>Choose Game Mode</h1>
<button onclick="window.location.href='/single_player'">Single Player</button>
<br><br>
<button onclick="window.location.href='/multiplayer'">Multiplayer</button>

</body>
</html>
"""

# HTML template for the Tic-Tac-Toe game
game_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tic-Tac-Toe</title>
    <style>
        body { font-family: sans-serif; text-align: center; margin-top: 50px; }
        table { margin: auto; border-collapse: collapse; }
        td { width: 100px; height: 100px; text-align: center; font-size: 3em; border: 1px solid #000; cursor: pointer; }
        td.x { color: red; }
        td.o { color: blue; }
        .game-over { font-size: 1.5em; color: green; }
        .restart-btn { margin-top: 20px; padding: 10px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .restart-btn:hover { background-color: #45a049; }
    </style>
</head>
<body>

<h1>Tic-Tac-Toe</h1>

{% if game_over %}
    <p class="game-over">{{ result }}</p>
    <button class="restart-btn" onclick="window.location.href='/restart'">Restart</button>
{% else %}
    <table>
        <tr>
            <td id="0" onclick="makeMove(0)" class="{{ board[0] }}">{{ board[0] }}</td>
            <td id="1" onclick="makeMove(1)" class="{{ board[1] }}">{{ board[1] }}</td>
            <td id="2" onclick="makeMove(2)" class="{{ board[2] }}">{{ board[2] }}</td>
        </tr>
        <tr>
            <td id="3" onclick="makeMove(3)" class="{{ board[3] }}">{{ board[3] }}</td>
            <td id="4" onclick="makeMove(4)" class="{{ board[4] }}">{{ board[4] }}</td>
            <td id="5" onclick="makeMove(5)" class="{{ board[5] }}">{{ board[5] }}</td>
        </tr>
        <tr>
            <td id="6" onclick="makeMove(6)" class="{{ board[6] }}">{{ board[6] }}</td>
            <td id="7" onclick="makeMove(7)" class="{{ board[7] }}">{{ board[7] }}</td>
            <td id="8" onclick="makeMove(8)" class="{{ board[8] }}">{{ board[8] }}</td>
        </tr>
    </table>
    <p>Current Turn: {{ current_turn }}</p>
{% endif %}

<p>Player: {{ nickname }}</p>
<p>Player X: {{ player_x }}</p>
<p>Player O: {{ player_o }}</p>

<script>
    function makeMove(cell) {
        window.location.href = '/move/' + cell;
    }
</script>

</body>
</html>
"""

# Function to run the Flask app
def run_flask():
    ip = get_ip()
    print(f"🚀 Flask app running! Access it from your phone: http://{ip}:5000")
    app.run(host="0.0.0.0", port=5000)

# Start Flask app in a separate thread
threading.Thread(target=run_flask).start()
