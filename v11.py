import random
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Global game rooms for multiplayer
rooms = {}

def generate_code():
    return str(random.randint(1000, 9999))

def initialize_game(players):
    game_state = {
        "board": ['' for _ in range(9)],
        "current_turn": 'X',
        "game_over": False,
        "result": "",
        "symbols": {players[0]: 'X', players[1]: 'O'},
        "players": players,
        "current_player": players[0]
    }
    return game_state

def check_win(game_state):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for condition in win_conditions:
        if game_state["board"][condition[0]] == game_state["board"][condition[1]] == game_state["board"][condition[2]] != '':
            game_state["game_over"] = True
            winner = game_state["board"][condition[0]]
            for player, symbol in game_state["symbols"].items():
                if symbol == winner:
                    game_state["result"] = f"{player} ({symbol}) wins!"
                    break
            return
    if '' not in game_state["board"]:
        game_state["game_over"] = True
        game_state["result"] = "It's a draw!"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['nickname'] = request.form['nickname']
        session['code'] = generate_code()
        return redirect(url_for('mode_select'))
    return render_template_string(nickname_form_html)

@app.route("/mode", methods=["GET"])
def mode_select():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template_string(mode_selection_html, nickname=session['nickname'])

@app.route("/multiplayer", methods=["GET", "POST"])
def multiplayer():
    if request.method == "POST":
        action = request.form.get('action')
        if action == 'create':
            room_code = generate_code()
            session['room'] = room_code
            rooms[room_code] = {"players": [session['nickname']], "state": None}
            return redirect(url_for('wait_for_player'))
        elif action == 'join':
            room_code = request.form['room_code']
            if room_code in rooms and len(rooms[room_code]['players']) < 2:
                rooms[room_code]['players'].append(session['nickname'])
                rooms[room_code]['state'] = initialize_game(rooms[room_code]['players'])
                session['room'] = room_code
                return redirect(url_for('game'))
            return "Room not found or full"
    return render_template_string(multiplayer_options_html)

@app.route("/wait")
def wait_for_player():
    room_code = session.get('room')
    if not room_code or room_code not in rooms:
        return redirect(url_for('multiplayer'))
    if len(rooms[room_code]["players"]) == 2:
        return redirect(url_for('game'))
    return render_template_string(wait_html, room=room_code)

@app.route("/game")
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    
    if 'room' not in session:
        return redirect(url_for('multiplayer'))
    
    room_code = session['room']
    if room_code not in rooms:
        return redirect(url_for('multiplayer'))
    
    game_state = rooms[room_code]['state']
    if not game_state:
        return redirect(url_for('wait_for_player'))
    
    player_symbol = game_state["symbols"].get(session['nickname'])
    is_my_turn = (game_state["current_player"] == session['nickname'])
    opponent = [p for p in game_state["players"] if p != session['nickname']][0]
    
    status_message = ""
    if game_state["game_over"]:
        status_message = "Game finished!"
    elif is_my_turn:
        status_message = f"Your turn ({player_symbol}) - PLAY NOW!"
    else:
        status_message = f"Waiting for {opponent}'s move..."
    
    return render_template_string(game_html,
                              board=game_state['board'],
                              game_over=game_state['game_over'],
                              result=game_state['result'],
                              nickname=session['nickname'],
                              player_symbol=player_symbol,
                              is_my_turn=is_my_turn,
                              opponent=opponent,
                              opponent_symbol=game_state["symbols"][opponent],
                              status_message=status_message)

@app.route("/move/<int:cell>")
def move(cell):
    if 'nickname' not in session or 'room' not in session:
        return redirect(url_for('multiplayer'))
    
    room_code = session['room']
    if room_code not in rooms:
        return redirect(url_for('multiplayer'))
    
    game_state = rooms[room_code]['state']
    if game_state["current_player"] != session['nickname'] or game_state["game_over"] or game_state["board"][cell] != '':
        return redirect(url_for('game'))
    
    game_state["board"][cell] = game_state["current_turn"]
    check_win(game_state)
    
    if not game_state["game_over"]:
        game_state["current_turn"] = 'O' if game_state["current_turn"] == 'X' else 'X'
        game_state["current_player"] = [p for p in game_state["players"] if p != session['nickname']][0]
    
    return redirect(url_for('game'))

@app.route("/restart")
def restart():
    if 'room' in session:
        room_code = session['room']
        if room_code in rooms:
            players = rooms[room_code]['state']["players"]
            rooms[room_code]['state'] = initialize_game(players)
    return redirect(url_for('game'))

@app.route("/exit")
def exit_game():
    if 'room' in session:
        room_code = session['room']
        if room_code in rooms:
            if len(rooms[room_code]['players']) == 2:
                opponent = [p for p in rooms[room_code]['players'] if p != session['nickname']][0]
                rooms[room_code]['state']['game_over'] = True
                rooms[room_code]['state']['result'] = f"⚠️ {session['nickname']} left the game. Returning to multiplayer..."
            del rooms[room_code]
    session.pop('room', None)
    return redirect(url_for('multiplayer'))

# HTML Templates (unchanged, except for removing single-player references)
nickname_form_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe | Enter Nickname</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #ff9a44;
            --dark: #2c3e50;
            --light: #f8f9fa;
            --success: #28a745;
            --danger: #dc3545;
        }
        * {
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        body {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        h2 {
            color: var(--dark);
            margin-bottom: 20px;
            font-weight: 600;
        }
        input {
            width: 100%;
            padding: 12px 15px;
            margin: 15px 0;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            border-color: var(--primary);
            outline: none;
        }
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s;
            font-weight: 600;
            margin-top: 10px;
        }
        button:hover {
            background-color: #3a5a8a;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Enter Your Nickname</h2>
        <form method="POST">
            <input type="text" name="nickname" placeholder="e.g., Player1" required>
            <button type="submit">Let's Play!</button>
        </form>
    </div>
</body>
</html>
'''

"""mode_selection_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe | Menu</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #ff9a44;
            --dark: #2c3e50;
            --light: #f8f9fa;
        }
        body {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }
        h2 {
            color: var(--dark);
            margin-bottom: 25px;
            font-weight: 600;
        }
        .btn {
            display: block;
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin: 10px 0;
            transition: all 0.3s;
            font-weight: 600;
            text-decoration: none;
        }
        .btn:hover {
            background-color: #3a5a8a;
            transform: translateY(-2px);
        }
        .btn-secondary {
            background-color: var(--secondary);
        }
        .btn-secondary:hover {
            background-color: #e68a3e;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome, {{ nickname }}!</h2>
        <a href="/multiplayer" class="btn">Multiplayer Mode</a>
    </div>
</body>
</html>
'''
"""


multiplayer_options_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe | Multiplayer</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #ff9a44;
            --dark: #2c3e50;
            --light: #f8f9fa;
            --danger: #dc3545;
        }
        body {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }
        h2 {
            color: var(--dark);
            margin-bottom: 20px;
            font-weight: 600;
        }
        input {
            width: 100%;
            padding: 12px 15px;
            margin: 15px 0;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            border-color: var(--primary);
            outline: none;
        }
        .btn {
            display: block;
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin: 10px 0;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn:hover {
            background-color: #3a5a8a;
            transform: translateY(-2px);
        }
        .btn-secondary {
            background-color: var(--secondary);
        }
        .btn-secondary:hover {
            background-color: #e68a3e;
        }
        .btn-danger {
            background-color: var(--danger);
        }
        .btn-danger:hover {
            background-color: #c82333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Multiplayer Options</h2>
        <form method="POST">
            <button type="submit" name="action" value="create" class="btn">Create New Room</button>
        </form>
        <form method="POST">
            <input type="text" name="room_code" placeholder="Enter Room Code" required>
            <input type="hidden" name="action" value="join">
            <button type="submit" class="btn btn-secondary">Join Room</button>
        </form>
        <a href="/mode" class="btn btn-danger">Back</a>
    </div>
</body>
</html>
'''

wait_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe | Waiting</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3">
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #ff9a44;
            --dark: #2c3e50;
            --light: #f8f9fa;
            --danger: #dc3545;
        }
        body {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }
        h2 {
            color: var(--dark);
            margin-bottom: 15px;
            font-weight: 600;
        }
        .room-code {
            font-size: 24px;
            font-weight: 700;
            color: var(--primary);
            margin: 20px 0;
            padding: 10px;
            background: rgba(74, 111, 165, 0.1);
            border-radius: 8px;
            display: inline-block;
        }
        .btn {
            display: block;
            background-color: var(--danger);
            color: white;
            border: none;
            padding: 15px 20px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin: 20px 0 0;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn:hover {
            background-color: #c82333;
            transform: translateY(-2px);
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid var(--primary);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Waiting for Opponent</h2>
        <p>Share this room code:</p>
        <div class="room-code">{{ room }}</div>
        <div class="loader"></div>
        <a href="/multiplayer" class="btn">Cancel</a>
    </div>
</body>
</html>
'''

game_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe | Game</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3">
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #ff9a44;
            --dark: #2c3e50;
            --light: #f8f9fa;
            --success: #28a745;
            --danger: #dc3545;
            --warning: #ffc107;
        }
        body {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .game-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: fadeIn 0.5s ease-out;
        }

        /* @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        } */
        .player-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            gap: 10px;
        }
        .player {
            padding: 10px 15px;
            border-radius: 8px;
            font-weight: 600;
            flex: 1;
            text-align: center;
        }
        .player.me {
            background: rgba(74, 111, 165, 0.1);
            color: var(--primary);
        }
        .player.opponent {
            background: rgba(255, 154, 68, 0.1);
            color: var(--secondary);
        }
        .status {
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            margin: 15px 0;
            animation: pulse 1.5s infinite;
        }
        /*
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        } */
        .status.your-turn {
            background: var(--success);
            color: white;
        }
        .status.waiting {
            background: var(--warning);
            color: var(--dark);
        }
        .status.game-over {
            background: var(--dark);
            color: white;
        }
        .result {
            font-size: 18px;
            font-weight: 700;
            margin: 15px 0;
            color: var(--primary);
        }
        table {
            margin: 20px auto;
            border-collapse: collapse;
        }
        td {
            width: 80px;
            height: 80px;
            text-align: center;
            font-size: 36px;
            font-weight: 700;
            cursor: pointer;
            border: 3px solid var(--dark);
            transition: all 0.2s;
        }
        td:hover {
            background: rgba(0, 0, 0, 0.05);
        }
        td:active {
            transform: scale(0.95);
        }
        .disabled td {
            pointer-events: none;
            opacity: 0.7;
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .btn {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            border: none;
        }
        .btn-restart {
            background: var(--primary);
            color: white;
        }
        .btn-restart:hover {
            background: #3a5a8a;
            transform: translateY(-2px);
        }
        .btn-exit {
            background: var(--danger);
            color: white;
        }
        .btn-exit:hover {
            background: #c82333;
            transform: translateY(-2px);
        }
        @media (max-width: 480px) {
            td {
                width: 70px;
                height: 70px;
                font-size: 32px;
            }
        }
    </style>
</head>
<body>
    <div class="game-container">
        <div class="player-info">
            <div class="player me">{{ nickname }} ({{ player_symbol }})</div>
            <div class="player opponent">{{ opponent }} ({{ opponent_symbol }})</div>
        </div>

        <div class="status {% if game_over %}game-over{% elif is_my_turn %}your-turn{% else %}waiting{% endif %}">
            {{ status_message }}
        </div>

        {% if game_over %}
        <div class="result">{{ result }}</div>
        {% endif %}

        <table {% if not is_my_turn or game_over %}class="disabled"{% endif %}>
            <tr>
                {% for i in range(3) %}
                <td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>
                {% endfor %}
            </tr>
            <tr>
                {% for i in range(3,6) %}
                <td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>
                {% endfor %}
            </tr>
            <tr>
                {% for i in range(6,9) %}
                <td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>
                {% endfor %}
            </tr>
        </table>

        <div class="actions">
            <button class="btn btn-restart" onclick="location.href='/restart'">Restart</button>
            <button class="btn btn-exit" onclick="location.href='/exit'">Exit</button>
        </div>
    </div>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)