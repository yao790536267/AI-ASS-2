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


class Board:

    def __init__(self, mycolor):

        # from part A
        edge = range(0, 8)
        self.blocks = sorted({(q, r) for q in edge for r in edge})


    def __contains__(self, qr):
        return qr in self.blocks

# state
# p, q, r => number of tokens in the stack,  x coodinate, y coordinate
class State:
    """
    Game state. including a board, white tokens and black tokens.
    """
    turn = None # current player, "white" or "black"
    board = None
    black_tokens = None
    white_tokens = None
    tokens = None # current stack, >0 means white, <0 means black

    def __init__(self, board, white_tokens, black_tokens):

        self.board = board
        self.black_tokens = black_tokens.copy()
        self.white_tokens = white_tokens.copy()

        self.tokens = Counter({xy:0 for xy in ALL_SQUARES})
        for qr in self.black_tokens:
            self.tokens[qr] = -self.black_tokens[qr]
        for qr in self.white_tokens:
            self.tokens[qr] = self.white_tokens[qr]

    def enemy_occupied(self, qr, enemy_color):
        if enemy_color == 'black':
            return qr in self.black_tokens
        else: #"black"
            return qr in self.white_tokens

    def get_legal_actions(self, color):
        """
        Get all legal next actions a white token can do.
        """
        if color == "white":
            enemy_color = "black"
            my_tokens = self.white_tokens.copy()
        else:
            enemy_color = "white"
            my_tokens = self.black_tokens.copy()

        legal_actions = []
        for qr in my_tokens:
            for step_directions_q, step_directions_r in STEP_DIRECTIONS:
                p = my_tokens.get(qr)
                q, r = qr
                for i in range(1, p + 1):
                    q_next = q + step_directions_q * i
                    r_next = r + step_directions_r * i
                    qr_next = q_next, r_next
                    if qr_next in self.board:
                        if not self.enemy_occupied(qr_next, enemy_color):
                            # move i tokens from qr to qr_next, the remaining number of token in (q, r) will be p-i
                            legal_actions.append(("MOVE", (i, qr, qr_next)))
            legal_actions.append(("BOOM", qr))
        return legal_actions

    def successor_state(self, action):
        """
        Get the resulting state given the action
        """
        atype, aargs = action
        new_state = State(self.board, self.white_tokens.copy(), self.black_tokens.copy())
        if atype == 'MOVE':
            i, qr, qr_next = aargs
            if self.tokens[qr] > 0: # white moves
                if new_state.white_tokens.get(qr) == i:
                    del new_state.white_tokens[qr]
                    self.tokens = 0

                else:
                    new_state.white_tokens[qr] -= i
                    self.tokens[qr] -= i
                if new_state.white_tokens.get(qr_next) is None:
                    new_state.white_tokens[qr_next] = i
                    self.tokens[qr_next] = i
                else:
                    new_state.white_tokens[qr_next] += i
                    self.tokens[qr_next] += i

            else: # black moves
                if new_state.black_tokens.get(qr) == i:
                    del new_state.black_tokens[qr]
                    self.tokens[qr] = 0

                else:
                    new_state.black_tokens[qr] -= i
                    self.tokens[qr] += i

                if new_state.black_tokens.get(qr_next) is None:
                    new_state.black_tokens[qr_next] = i
                    self.tokens[qr_next] = -i
                else:
                    new_state.white_tokens[qr_next] += i
                    self.tokens[qr_next] -= i


        if atype == "BOOM":
            qr = aargs
            new_state = State(self.board, self.white_tokens.copy(), self.black_tokens.copy())
            board_tokens = new_state.white_tokens.copy()
            board_tokens.update(new_state.black_tokens)
            boom_queue = queue.Queue()
            boom_list = []
            if self.tokens[qr] > 0:
                boom_queue.put((qr, 'white'))
                boom_list.append((qr, 'white'))
            else:  # black
                boom_queue.put((qr, 'black'))
                boom_list.append((qr, 'black'))
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
                        if qr_next_boom in new_state.white_tokens:
                            boom_queue.put((qr_next_boom, 'white'))
                            boom_list.append((qr_next_boom, 'white'))
                        else:
                            boom_queue.put((qr_next_boom, 'black'))
                            boom_list.append((qr_next_boom, 'black'))
            for token in boom_list:
                qr, colour = token
                new_state.tokens[qr] = 0
                if colour == 'white':
                    del new_state.white_tokens[qr]
                else:
                    del new_state.black_tokens[qr]

        return new_state






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

