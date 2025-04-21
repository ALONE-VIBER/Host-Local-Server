import time
import threading
import socket
import random
import os
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Global game rooms for multiplayer
rooms = {}

# Get local IP for access

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

def write_log(nickname, message):
    filename = f"logs/{nickname}.txt"
    os.makedirs("logs", exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def generate_code():
    return str(random.randint(1000, 9999))

def initialize_game():
    return {
        "board": ['' for _ in range(9)],
        "current_turn": 'X',
        "game_over": False,
        "result": ""
    }

def check_win(game_state):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for condition in win_conditions:
        if game_state["board"][condition[0]] == game_state["board"][condition[1]] == game_state["board"][condition[2]] != '':
            game_state["game_over"] = True
            game_state["result"] = f"{game_state['board'][condition[0]]} wins!"
            return
    if '' not in game_state["board"]:
        game_state["game_over"] = True
        game_state["result"] = "It's a draw!"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        nickname = request.form['nickname']
        code = generate_code()
        session['nickname'] = nickname
        session['code'] = code
        write_log(nickname, f"👋 Joined with code {code}")
        return redirect(url_for('mode_select'))
    return render_template_string(nickname_form_html)

@app.route("/mode", methods=["GET"])
def mode_select():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template_string(mode_selection_html, nickname=session['nickname'], code=session['code'])

@app.route("/single")
def single_player():
    session['game_state'] = initialize_game()
    write_log(session['nickname'], "🎮 Started Single Player Game")
    return redirect(url_for('game'))

@app.route("/multiplayer")
def multiplayer():
    room_code = generate_code()
    session['room'] = room_code
    rooms[room_code] = {"players": [session['nickname']], "state": initialize_game()}
    write_log(session['nickname'], f"🏠 Created Room {room_code}")
    return redirect(url_for('wait_for_player'))

@app.route("/wait")
def wait_for_player():
    room_code = session.get('room')
    if not room_code or room_code not in rooms:
        return redirect(url_for('mode_select'))
    if len(rooms[room_code]["players"]) == 2:
        return redirect(url_for('game'))
    return render_template_string(wait_html, room=room_code)

@app.route("/join", methods=["POST"])
def join_room():
    room_code = request.form['room_code']
    nickname = request.form['nickname']
    if room_code in rooms and len(rooms[room_code]['players']) < 2:
        rooms[room_code]['players'].append(nickname)
        session['nickname'] = nickname
        session['room'] = room_code
        write_log(nickname, f"👥 Joined Room {room_code}")
        return redirect(url_for('game'))
    return "Room not found or full"

@app.route("/game")
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    game_state = None
    if 'room' in session:
        game_state = rooms[session['room']]['state']
    else:
        game_state = session.get('game_state', initialize_game())
    return render_template_string(game_html,
                                  board=game_state['board'],
                                  current_turn=game_state['current_turn'],
                                  game_over=game_state['game_over'],
                                  result=game_state['result'],
                                  nickname=session['nickname'],
                                  code=session['code'])

@app.route("/move/<int:cell>")
def move(cell):
    if 'nickname' not in session:
        return redirect(url_for('index'))
    if 'room' in session:
        game_state = rooms[session['room']]['state']
    else:
        game_state = session.get('game_state')
    if not game_state or game_state["game_over"] or game_state["board"][cell] != '':
        return redirect(url_for('game'))

    game_state["board"][cell] = game_state["current_turn"]
    write_log(session['nickname'], f"🎯 Move: {cell} => {game_state['current_turn']}")
    check_win(game_state)

    if not game_state["game_over"]:
        game_state["current_turn"] = 'O' if game_state["current_turn"] == 'X' else 'X'

    if 'room' not in session:
        session['game_state'] = game_state

    return redirect(url_for('game'))

@app.route("/restart")
def restart():
    if 'room' in session:
        rooms[session['room']]['state'] = initialize_game()
    else:
        session['game_state'] = initialize_game()
    write_log(session['nickname'], "🔄 Restarted the Game")
    return redirect(url_for('game'))

@app.route("/exit")
def exit_game():
    write_log(session['nickname'], "🚪 Exited the Game")
    session.clear()
    return redirect(url_for('index'))

nickname_form_html = '''
<form method="POST">
    <h2>Enter your nickname</h2>
    <input type="text" name="nickname" required />
    <button type="submit">Enter</button>
</form>
'''

mode_selection_html = '''
<h2>Welcome {{ nickname }} ({{ code }})</h2>
<a href="/single"><button>Single Player</button></a>
<a href="/multiplayer"><button>Multiplayer</button></a>
<form method="POST" action="/join">
    <input name="room_code" placeholder="Enter Room Code" required>
    <input name="nickname" type="hidden" value="{{ nickname }}">
    <button type="submit">Join Room</button>
</form>
'''

wait_html = '''
<h2>Waiting for opponent to join Room {{ room }}...</h2>
<meta http-equiv="refresh" content="3">
'''

game_html = '''
<h2>Player: {{ nickname }} | Code: {{ code }}</h2>
<table border="1">
<tr>{% for i in range(3) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
<tr>{% for i in range(3,6) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
<tr>{% for i in range(6,9) %}<td onclick="location.href='/move/{{ i }}'">{{ board[i] }}</td>{% endfor %}</tr>
</table>
<p>Current Turn: {{ current_turn }}</p>
{% if game_over %}<p>{{ result }}</p>{% endif %}
<a href="/restart">Restart</a> | <a href="/exit">Exit</a>
'''

if __name__ == "__main__":
    ip = get_ip()
    print(f"Access from phone: http://{ip}:5000")
    app.run(host="0.0.0.0", port=5000)
