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
    <title>Tic Tac Toe</title>
    <style>body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    input { padding: 10px; margin: 10px 0; width: 80%; border: 1px solid #ddd; border-radius: 5px; }
    button { background-color: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 80%; }
    button:hover { background-color: #45a049; }</style>
</head>
<body>
    <div class="container">
        <form method="POST">
            <h2>Enter your nickname</h2>
            <input type="text" name="nickname" required />
            <button type="submit">Enter</button>
        </form>
    </div>
</body>
</html>
'''

mode_selection_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Tic Tac Toe</title>
    <style>body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    button { background-color: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 80%; margin: 5px; }
    button:hover { background-color: #45a049; }</style>
</head>
<body>
    <div class="container">
        <h2>Welcome {{ nickname }}</h2>
        <a href="/multiplayer"><button>Multiplayer</button></a>
    </div>
</body>
</html>
'''

multiplayer_options_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Multiplayer</title>
    <style>body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    input { padding: 10px; margin: 10px 0; width: 80%; border: 1px solid #ddd; border-radius: 5px; }
    button { background-color: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 80%; margin: 5px; }
    button:hover { background-color: #45a049; }
    .back-btn { background-color: #f44336; }</style>
</head>
<body>
    <div class="container">
        <h2>Multiplayer Options</h2>
        <form method="POST">
            <button type="submit" name="action" value="create">Create New Room</button>
        </form>
        <form method="POST">
            <input type="text" name="room_code" placeholder="Enter Room Code" required>
            <input type="hidden" name="action" value="join">
            <button type="submit">Join Existing Room</button>
        </form>
        <a href="/mode"><button class="back-btn">Back</button></a>
    </div>
</body>
</html>
'''

wait_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Waiting</title>
    <style>body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    .back-btn { background-color: #f44336; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 80%; }</style>
    <meta http-equiv="refresh" content="3">
</head>
<body>
    <div class="container">
        <h2>Waiting for opponent in Room {{ room }}...</h2>
        <p>Share this code with your friend!</p>
        <a href="/multiplayer"><button class="back-btn">Cancel</button></a>
    </div>
</body>
</html>
'''

game_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Game</title>
    <style>body { font-family: Arial; display: flex; flex-direction: column; align-items: center; padding: 20px; }
    .game-container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }
    td { width: 60px; height: 60px; text-align: center; font-size: 24px; cursor: pointer; border: 2px solid #333; }
    button { background-color: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
    .back-btn { background-color: #f44336; }
    .disabled { pointer-events: none; opacity: 0.6; }</style>
    <meta http-equiv="refresh" content="3">
</head>
<body>
    <div class="game-container">
        <div class="player-info">
            <div>You: {{ nickname }} ({{ player_symbol }})</div>
            <div>Opponent: {{ opponent }} ({{ opponent_symbol }})</div>
        </div>
        <div>{{ status_message }}</div>
        {% if game_over %}<div>{{ result }}</div>{% endif %}
        <table {% if not is_my_turn or game_over %}class="disabled"{% endif %}>
            <tr>{% for i in range(3) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
            <tr>{% for i in range(3,6) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
            <tr>{% for i in range(6,9) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
        </table>
        <div>
            <a href="/restart"><button>Restart</button></a>
            <a href="/exit"><button class="back-btn">Exit</button></a>
        </div>
    </div>
</body>
</html>
'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)