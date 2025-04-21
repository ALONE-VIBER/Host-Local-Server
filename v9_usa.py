import threading
import socket
import random
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

rooms = {}

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

def generate_code():
    return str(random.randint(1000, 9999))

def initialize_game(players=None):
    game_state = {
        "board": ['' for _ in range(9)],
        "current_turn": 'X',
        "game_over": False,
        "result": "",
        "symbols": {},
        "players": []
    }
    if players and len(players) == 2:
        random.shuffle(players)
        game_state["symbols"] = {
            players[0]: 'X',
            players[1]: 'O'
        }
        game_state["current_player"] = players[0]
        game_state["players"] = players
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
        nickname = request.form['nickname']
        code = generate_code()
        session['nickname'] = nickname
        session['code'] = code
        return redirect(url_for('mode_select'))
    return render_template_string(nickname_form_html)

@app.route("/mode", methods=["GET"])
def mode_select():
    if 'nickname' not in session:
        return redirect(url_for('index'))
    return render_template_string(mode_selection_html, nickname=session['nickname'], code=session['code'])

@app.route("/multiplayer", methods=["GET", "POST"])
def multiplayer():
    if request.method == "POST":
        action = request.form.get('action')
        if action == 'create':
            room_code = generate_code()
            session['room'] = room_code
            rooms[room_code] = {
                "players": [session['nickname']],
                "state": None
            }
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
        return redirect(url_for('mode_select'))
    if len(rooms[room_code]["players"]) == 2:
        return redirect(url_for('game'))
    return render_template_string(wait_html, room=room_code)

@app.route("/game")
def game():
    if 'nickname' not in session:
        return redirect(url_for('index'))

    if 'room' in session:
        room_code = session['room']
        if room_code not in rooms:
            return redirect(url_for('mode_select'))

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
                                      current_turn=game_state['current_turn'],
                                      game_over=game_state['game_over'],
                                      result=game_state['result'],
                                      nickname=session['nickname'],
                                      code=session['code'],
                                      player_symbol=player_symbol,
                                      is_my_turn=is_my_turn,
                                      opponent=opponent,
                                      opponent_symbol=game_state["symbols"][opponent],
                                      current_player=game_state["current_player"],
                                      status_message=status_message)
    return redirect(url_for('mode_select'))

@app.route("/move/<int:cell>")
def move(cell):
    if 'nickname' not in session:
        return redirect(url_for('index'))

    if 'room' in session:
        room_code = session['room']
        if room_code not in rooms:
            return redirect(url_for('game'))

        game_state = rooms[room_code]['state']
        if game_state["current_player"] != session['nickname']:
            return redirect(url_for('game'))

        if game_state["game_over"] or game_state["board"][cell] != '':
            return redirect(url_for('game'))

        game_state["board"][cell] = game_state["current_turn"]
        check_win(game_state)

        if not game_state["game_over"]:
            game_state["current_turn"] = 'O' if game_state["current_turn"] == 'X' else 'X'
            other_player = [p for p in game_state["players"] if p != session['nickname']][0]
            game_state["current_player"] = other_player

        return redirect(url_for('game'))
    return redirect(url_for('mode_select'))

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
    if 'room' in session and session['room'] in rooms:
        room_code = session['room']
        if len(rooms[room_code]['players']) == 1:
            del rooms[room_code]
        else:
            remaining_player = [p for p in rooms[room_code]['players'] if p != session['nickname']][0]
            rooms[room_code]['state']['game_over'] = True
            rooms[room_code]['state']['result'] = "Opponent left. Returning to multiplayer menu..."
            rooms[room_code]['players'].remove(session['nickname'])
    session.clear()
    return redirect(url_for('multiplayer'))

# Include the same HTML templates: nickname_form_html, mode_selection_html, multiplayer_options_html, wait_html, game_html here

if __name__ == "__main__":
    ip = get_ip()
    print(f"Access from phone: http://{ip}:5000")
    app.run(host="0.0.0.0", port=5000)
