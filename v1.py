import time
import threading
import socket
import random
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random string

# Thread-safe log function
log_lock = threading.Lock()
def log_event(message):
    def write_log():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_lock:
            with open("logs.txt", "a") as f:
                f.write(f"[{timestamp}] {message}\n")
    threading.Thread(target=write_log).start()

# Get local IP for phone access
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP

# Resolve device hostname
def get_device_hostname(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except socket.herror:
        hostname = ip
    return hostname

# Generate a unique 4-digit code
def generate_unique_code():
    return random.randint(1000, 9999)

# Game state
def initialize_game():
    return {
        "board": ['' for _ in range(9)],
        "current_turn": 'X',
        "game_over": False,
        "result": "",
    }

# Check win condition
def check_win(game_state):
    win_conditions = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ]
    for condition in win_conditions:
        a, b, c = condition
        if game_state["board"][a] == game_state["board"][b] == game_state["board"][c] and game_state["board"][a] != '':
            game_state["game_over"] = True
            game_state["result"] = f"{game_state['board'][a]} wins!"
            return
    if '' not in game_state["board"]:
        game_state["game_over"] = True
        game_state["result"] = "It's a draw!"

# Before each request
@app.before_request
def log_access():
    ip = request.remote_addr
    log_event(f"🌐 Access from {ip} to {request.path}")

# Home page: get nickname
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['nickname'] = request.form['nickname']
        session['user_code'] = generate_unique_code()
        session['game_state'] = initialize_game()
        log_event(f"🎮 Game started by {session['nickname']}#{session['user_code']}")
        return redirect(url_for('game'))
    return render_template_string(nickname_form_html)

# Game page
@app.route("/game")
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))

    game_state = session.get('game_state', initialize_game())
    device_hostname = get_device_hostname(request.remote_addr)
    return render_template_string(game_html,
                                  board=game_state["board"],
                                  current_turn=game_state["current_turn"],
                                  game_over=game_state["game_over"],
                                  result=game_state["result"],
                                  device_hostname=device_hostname,
                                  nickname=session['nickname'],
                                  user_code=session['user_code'])

# Make a move
@app.route("/move/<int:cell>")
def move(cell):
    if 'nickname' not in session:
        return redirect(url_for('index'))

    game_state = session.get('game_state', initialize_game())

    if game_state["game_over"] or game_state["board"][cell] != '':
        return redirect(url_for('game'))

    game_state["board"][cell] = game_state["current_turn"]
    log_event(f"🕹 {session['nickname']}#{session['user_code']} played '{game_state['current_turn']}' at cell {cell}")
    check_win(game_state)

    if not game_state["game_over"]:
        game_state["current_turn"] = 'O' if game_state["current_turn"] == 'X' else 'X'

    session['game_state'] = game_state
    return redirect(url_for('game'))

# Restart game
@app.route("/restart")
def restart():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    session['game_state'] = initialize_game()
    log_event(f"🔄 Game restarted by {session['nickname']}#{session['user_code']}")
    return redirect(url_for('game'))

# Exit game
@app.route("/exit")
def exit_game():
    log_event(f"👋 {session.get('nickname')}#{session.get('user_code')} exited the game")
    session.clear()
    return redirect(url_for('index'))

# HTML: Nickname form
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
<form method="POST">
    <input type="text" name="nickname" placeholder="Enter Nickname" required>
    <br><br>
    <button class="submit-btn" type="submit">Start Game</button>
</form>
</body>
</html>
"""

# HTML: Game screen
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
        td { width: 100px; height: 100px; text-align: center; font-size: 2em; border: 1px solid #000; cursor: pointer; }
        td.x { color: red; }
        td.o { color: blue; }
        .game-over { font-size: 1.5em; color: green; }
        .restart-btn { margin-top: 20px; padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .restart-btn:hover { background-color: #45a049; }
        .top-left { position: absolute; top: 10px; left: 10px; font-weight: bold; }
    </style>
</head>
<body>

<p class="top-left">Player: {{ nickname }}#{{ user_code }}</p>

<h1>Tic-Tac-Toe</h1>

{% if game_over %}
    <p class="game-over">{{ result }}</p>
    <button class="restart-btn" onclick="window.location.href='/restart'">Restart</button>
    <button class="restart-btn" onclick="window.location.href='/exit'">Exit</button>
{% else %}
    <table>
        <tr>
            <td onclick="makeMove(0)" class="{{ board[0] }}">{{ board[0] }}</td>
            <td onclick="makeMove(1)" class="{{ board[1] }}">{{ board[1] }}</td>
            <td onclick="makeMove(2)" class="{{ board[2] }}">{{ board[2] }}</td>
        </tr>
        <tr>
            <td onclick="makeMove(3)" class="{{ board[3] }}">{{ board[3] }}</td>
            <td onclick="makeMove(4)" class="{{ board[4] }}">{{ board[4] }}</td>
            <td onclick="makeMove(5)" class="{{ board[5] }}">{{ board[5] }}</td>
        </tr>
        <tr>
            <td onclick="makeMove(6)" class="{{ board[6] }}">{{ board[6] }}</td>
            <td onclick="makeMove(7)" class="{{ board[7] }}">{{ board[7] }}</td>
            <td onclick="makeMove(8)" class="{{ board[8] }}">{{ board[8] }}</td>
        </tr>
    </table>
    <p>Current Turn: {{ current_turn }}</p>
{% endif %}

<p>Accessed by: {{ device_hostname }}</p>

<script>
    function makeMove(cell) {
        window.location.href = '/move/' + cell;
    }
</script>

</body>
</html>
"""

# Run Flask app
def run_flask():
    ip = get_ip()
    print(f"🚀 Flask app running! Access from phone: http://{ip}:5000")
    app.run(host="0.0.0.0", port=5000)

# Start Flask server in a thread
threading.Thread(target=run_flask).start()
