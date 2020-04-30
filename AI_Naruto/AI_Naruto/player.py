import sys
import json
import queue
import time

from collections import Counter
from AI_Naruto.util import print_move, print_boom, print_board, PriorityQueue

STEP_DIRECTIONS = [(-1, +0), (+1, +0), (+0, -1), (+0, +1)]
BOOM_DIRECTIONS = [(-1, +0), (+1, +0), (+0, -1), (+0, +1), (-1, +1), (+1, +1), (+1, -1), (-1, -1)]

ALL_SQUARES = {(x, y) for x in range(8) for y in range(8)}

BLACK_INITIAL_SQUARES = [(0, 7), (1, 7), (3, 7), (4, 7), (6, 7), (7, 7),
                         (0,6), (1,6), (3,6), (4,6), (6,6), (7,6)]
WHITE_INITIAL_SQUARES = [(0, 1), (1, 1), (3, 1), (4, 1), (6, 1), (7, 1),
                         (0,0), (1,0), (3,0), (4,0), (6,0), (7,0)]

MAX_DEPTH = 5  # the maximum depth that minimax algorithm explores

def _NEAR_SQUARES(square):
    x, y = square
    return {(x-1,y+1),(x,y+1),(x+1,y+1),
            (x-1,y),          (x+1,y),
            (x-1,y-1),(x,y-1),(x+1,y-1)} & ALL_SQUARES

def heuristic(state):
    """
    Heuristic function. Return the minimum manhattan distance
    between one of white token and one of the black token.
    Return 0 when no black (enemy) tokens on board.
    """
    dist = 2147483647
    if len(state.enemies) == 0:
        return 0

    for my_token in state.my_tokens.keys():
        for enemy_token in state.enemies.keys():
            xy1 = my_token
            xy2 = enemy_token
            dist = min(dist, abs(xy1[0] - xy2[0]) + abs(xy1[1] - xy2[1]))
    return dist

class Board:

    def __init__(self, mycolor):
        self.board = Counter({xy:0 for xy in ALL_SQUARES})
        self.curent_white_dict = dict()
        self.curent_black_dict = dict()
        self.mycolor = mycolor

        #白色用正数表示token数量，黑色用负数表示token数量
        for xy in WHITE_INITIAL_SQUARES:
            self.board[xy] += 1
            self.curent_white_dict[xy] = 1

        for xy in BLACK_INITIAL_SQUARES:
            self.board[xy] -= 1
            self.curent_black_dict[xy] = 1
        self.score = {'white': 12, 'black': 12}

        # from part A
        edge = range(0, 8)
        self.blocks = sorted({(q, r) for q in edge for r in edge})

#update the board
    def update(self, color, action):
        atype, *aargs = action
        if atype == "MOVE":
            n, a, b = aargs
            n = -n if self.board[a] < 0 else n
            self.board[a] -= n
            self.board[b] += n
            if color == 'white':
                self.curent_white_dict[a] -= n
                if b in self.curent_white_dict.keys():
                    self.curent_white_dict[b] += n
                else:
                    self.curent_white_dict[b] = n

            if color == 'black':
                self.curent_black_dict[a] -= n
                if b in self.curent_black_dict.keys():
                    self.curent_black_dict[b] += n
                else:
                    self.curent_black_dict[b] = n

        else:  # atype == "BOOM":
            start_square, = aargs
            to_boom = [start_square]
            for boom_square in to_boom:
                n = self.board[boom_square]
                self.score["white" if n > 0 else "black"] -= abs(n)
                self.board[boom_square] = 0
                self.curent_white_dict.pop(boom_square)
                self.curent_black_dict.pop(boom_square)
                for near_square in _NEAR_SQUARES(boom_square):
                    if self.board[near_square] != 0:
                        to_boom.append(near_square)

    def __contains__(self, qr):
        return qr in self.blocks

# state
# p, q, r => number of tokens in the stack,  x coodinate, y coordinate
class State:
    """
    Game state. including a board, white (my_token) tokens and black (enemy) tokens.
    """
    board = None
    enemies = None
    my_tokens = None

    def __init__(self, board, my_tokens, enemies):

        self.board = board
        self.enemies = enemies.copy()
        self.my_tokens = my_tokens.copy()

    def enemy_occupied(self, qr):
        return qr in self.enemies

    def get_legal_actions(self):
        """
        Get all legal next actions a white token can do.
        """
        legal_actions = []
        for qr in self.my_tokens:
            for step_directions_q, step_directions_r in STEP_DIRECTIONS:
                p = self.my_tokens.get(qr)
                q, r = qr
                for i in range(1, p + 1):
                    q_next = q + step_directions_q * i
                    r_next = r + step_directions_r * i
                    qr_next = q_next, r_next
                    if qr_next in self.board:
                        if not self.enemy_occupied(qr_next):
                            # move i tokens from qr to qr_next, the remaining number of token in (q, r) will be p-i
                            legal_actions.append(("MOVE", (i, qr, qr_next)))
            legal_actions.append(("BOOM", qr))
        return legal_actions

    def successor_state(self, action):
        """
        Get the resulting state given the action
        """
        atype, aargs = action
        new_state = State(self.board, self.my_tokens.copy(), self.enemies.copy())
        if atype == 'MOVE':
            i, qr, qr_next = aargs
            if new_state.my_tokens.get(qr) == i:
                del new_state.my_tokens[qr]
                if new_state.my_tokens.get(qr_next) is None:
                    new_state.my_tokens[qr_next] = i
                else:
                    new_state.my_tokens[qr_next] += i
            else:
                new_state.my_tokens[qr] -= i
                if new_state.my_tokens.get(qr_next) is None:
                    new_state.my_tokens[qr_next] = i
                else:
                    new_state.my_tokens[qr_next] += i

        if atype == "BOOM":
            qr = aargs
            new_state = State(self.board, self.my_tokens.copy(), self.enemies.copy())
            board_tokens = new_state.my_tokens.copy()
            board_tokens.update(new_state.enemies)
            boom_queue = queue.Queue()
            boom_list = []
            boom_queue.put((qr, 'white'))
            boom_list.append((qr, 'white'))
            while not boom_queue.empty():
                boom_token = boom_queue.get()
                q, r = boom_token[0]
                for boom_directions_q, boom_directions_r in BOOM_DIRECTIONS:
                    q_next_boom = q + boom_directions_q
                    r_next_boom = r + boom_directions_r
                    qr_next_boom = q_next_boom, r_next_boom
                    if qr_next_boom in board_tokens and \
                            (qr_next_boom, 'white') not in boom_list and \
                            (qr_next_boom, 'black') not in boom_list:
                        if qr_next_boom in new_state.my_tokens:
                            boom_queue.put((qr_next_boom, 'white'))
                            boom_list.append((qr_next_boom, 'white'))
                        else:
                            boom_queue.put((qr_next_boom, 'black'))
                            boom_list.append((qr_next_boom, 'black'))
            for token in boom_list:
                qr, colour = token
                if colour == 'white':
                    del new_state.my_tokens[qr]
                else:
                    del new_state.enemies[qr]

        return new_state

    def is_goal(self):
        """
        The goal of the game is that no enemies on board
        """
        return len(self.enemies) == 0





class AI_NarutoPlayer:


    turns = 0  # current turn
    color = None
    opponent_color = None
    board = None
    state = None


    def __init__(self, colour):
        """
        This method is called once at the beginning of the game to initialise
        your player. You should use this opportunity to set up your own internal
        representation of the game state, and any other information about the 
        game state you would like to maintain for the duration of the game.

        The parameter colour will be a string representing the player your 
        program will play as (White or Black). The value will be one of the 
        strings "white" or "black" correspondingly.
        """
        # TODO: Set up state representation.

        self.color = colour
        self.board = Board(self.color)
        if(self.color == 'white'):
            self.opponent_color = 'black'
            self.init_my_tokens = self.board.curent_white_dict.copy()
            self.init_opponent_tokens = self.board.curent_black_dict.copy()
        else:
            self.opponent_color = 'white'
            self.init_my_tokens = self.board.curent_black_dict.copy()
            self.init_opponent_tokens = self.board.curent_white_dict.copy()

        # initialise state
        self.state = State(self.board, self.init_my_tokens, self.init_opponent_tokens)




    def action(self):
        """
        This method is called at the beginning of each of your turns to request 
        a choice of action from your program.

        Based on the current state of the game, your player should select and 
        return an allowed action to play on this turn. The action must be
        represented based on the spec's instructions for representing actions.
        """
        # TODO: Decide what action to take, and return it
        return ("BOOM", (0, 0))


    def update(self, colour, action):
        """
        This method is called at the end of every turn (including your player’s 
        turns) to inform your player about the most recent action. You should 
        use this opportunity to maintain your internal representation of the 
        game state and any other information about the game you are storing.

        The parameter colour will be a string representing the player whose turn
        it is (White or Black). The value will be one of the strings "white" or
        "black" correspondingly.

        The parameter action is a representation of the most recent action
        conforming to the spec's instructions for representing actions.

        You may assume that action will always correspond to an allowed action 
        for the player colour (your method does not need to validate the action
        against the game rules).
        """
        # TODO: Update state representation in response to action.

        self.board.update(colour, action)

    def get_possible_moves(self, token):
        possible_moves = []
        for step_directions_q, step_directions_r in STEP_DIRECTIONS:
            p = self.my_tokens.get(token)
            q, r = token
            for i in range(1, p + 1):
                q_next = q + step_directions_q * i
                r_next = r + step_directions_r * i
                qr_next = q_next, r_next
                if qr_next in self.board:
                    if not self.enemy_occupied(qr_next):
                        # move i tokens from qr to qr_next, the remaining number of token in (q, r) will be p-i
                        possible_moves.append(("MOVE", (i, token, qr_next)))
        # possible_moves.append(("BOOM", token))

        return possible_moves

    def alphabeta(self, pos, current_depth, alpha, beta):
        # increase depth
        current_depth += 1

        # if max depth is reached
        if current_depth == MAX_DEPTH:
            # apply evaluation function
            return self.get_heuristic()

        if current_depth % 2 == 0:
            # min player's turn
            # loop all enemy pieces of our player
            remaining_pieces = self.enemies
            for token in remaining_pieces:
                posible_actions = self.get_possible_moves(token)
                #check if the piece can move
                if len(posible_actions) == 0:
                    continue
                else:
                    for new_pos in posible_actions:
                        old_pos = token.pos
                        #alpha beta pruning
                        if alpha < beta:
                            # move the piece into the aim square
                            eliminated_pieces = token.makemove(new_pos)
                            current_heuristic = self.alphabeta(new_pos, current_depth, alpha, beta)
                            # undo move
                            token.undomove(old_pos, eliminated_pieces)
                            #update beta
                            if beta > current_heuristic:
                                beta = current_heuristic
            return beta
        else:
            #max player's turn
            #loop all friend pieces of our player
            remaing_pieces = [p for p in self.friend_pieces() if p.alive]
            for token in remaing_pieces:
                possible_moves = token.moves()
                #check if this piece can move
                if len(possible_moves) == 0:
                    continue
                else:
                    for new_pos in possible_moves:
                        #record old_pos for undo
                        old_pos = token.pos
                        #do alpha beta pruning
                        if alpha < beta:
                            #move the piece into the aim square
                            eliminated_pieces = token.makemove(new_pos)
                            current_heuristic = self.alphabeta(new_pos, current_depth, alpha, beta)
                            #undo move
                            token.undomove(old_pos, eliminated_pieces)
                            #update alpha
                            if alpha < current_heuristic:
                                alpha = current_heuristic
            return alpha

