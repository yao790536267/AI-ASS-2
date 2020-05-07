import queue
import AI_Naruto.util as util

STEP_DIRECTIONS = [(-1, +0), (+1, +0), (+0, -1), (+0, +1)]
BOOM_DIRECTIONS = [(-1, +0), (+1, +0), (+0, -1), (+0, +1), (-1, +1), (+1, +1), (+1, -1), (-1, -1)]

ALL_SQUARES = {(x, y) for x in range(8) for y in range(8)}

BLACK_INITIAL_SQUARES = [(0, 7), (1, 7), (3, 7), (4, 7), (6, 7), (7, 7),
                         (0, 6), (1, 6), (3, 6), (4, 6), (6, 6), (7, 6)]
WHITE_INITIAL_SQUARES = [(0, 1), (1, 1), (3, 1), (4, 1), (6, 1), (7, 1),
                         (0, 0), (1, 0), (3, 0), (4, 0), (6, 0), (7, 0)]

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
    color = None # current player, "white" or "black"
    board = None
    opponent_tokens = None
    my_tokens = None
    tokens = None # current stack, >0 means white, <0 means black
    actioned_color = None       # actioned color
    opponent_color = None        # color which will action

    def __init__(self, color, board, my_tokens, opponent_tokens):

        self.color = color
        if self.color == 'white':
            self.opponent_color = 'black'
        else:
            self.opponent_color = 'white'

        self.board = board
        self.my_tokens = my_tokens.copy()
        self.opponent_tokens = opponent_tokens.copy()

    def opponent_occupied(self, qr):
        return qr in self.opponent_tokens

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
                        #if not self.enemy_occupied(qr_next, enemy_color):
                        if not self.opponent_occupied(qr_next):
                            # move i tokens from qr to qr_next, the remaining number of token in (q, r) will be p-i
                            legal_actions.append(("MOVE", (i, qr, qr_next)))
            legal_actions.append(("BOOM", qr))
        return legal_actions

    def successor_state(self, action):
        """
        Get the resulting state given the action
        """

        atype, aargs = action
        my_tokens = self.my_tokens.copy()
        opponent_tokens = self.opponent_tokens.copy()

        if atype == 'MOVE':
            i, qr, qr_next = aargs
            if my_tokens.get(qr) == i:
                del my_tokens[qr]
                if my_tokens.get(qr_next) is None:
                    my_tokens[qr_next] = i
                else:
                    my_tokens[qr_next] += i
            else:
                my_tokens[qr] -= i
                if my_tokens.get(qr_next) is None:
                    my_tokens[qr_next] = i
                else:
                    my_tokens[qr_next] += i


        if atype == "BOOM":
            qr = aargs

            board_tokens = my_tokens.copy()
            board_tokens.update(opponent_tokens)
            boom_queue = queue.Queue()
            boom_list = []
            boom_queue.put((qr, self.color))
            boom_list.append((qr, self.color))
            while not boom_queue.empty():
                boom_token = boom_queue.get()
                q, r = boom_token[0]
                for boom_directions_q, boom_directions_r in BOOM_DIRECTIONS:
                    q_next_boom = q + boom_directions_q
                    r_next_boom = r + boom_directions_r
                    qr_next_boom = q_next_boom, r_next_boom
                    if qr_next_boom in board_tokens and \
                            (qr_next_boom, self.color) not in boom_list and \
                            (qr_next_boom, self.opponent_color) not in boom_list:
                        if qr_next_boom in my_tokens:
                            boom_queue.put((qr_next_boom, self.color))
                            boom_list.append((qr_next_boom, self.color))
                        else:
                            boom_queue.put((qr_next_boom, self.opponent_color))
                            boom_list.append((qr_next_boom, self.opponent_color))
            for token in boom_list:
                qr, colour = token
                if colour == self.color:
                    del my_tokens[qr]
                else:
                    del opponent_tokens[qr]

        #Next state's my_tokens is this state's opponent_tokens
        new_state = State(self.opponent_color, self.board, opponent_tokens.copy(), my_tokens.copy())
        return new_state

    def evaluation(self):
        my_token_number = 0
        opponent_token_number = 0
        my_token_average_x = 0
        my_token_average_y = 0
        opponent_token_average_x = 0
        opponent_token_average_y = 0

        if len(self.opponent_tokens) == 0:
            return 999
        if len(self.my_tokens) == 0:
            return -999

        for key in self.my_tokens.keys():
            my_token_number += self.my_tokens[key]
            x, y = key
            my_token_average_x += x
            my_token_average_y += y

        for key in self.opponent_tokens.keys():
            opponent_token_number += self.opponent_tokens[key]
            x, y = key
            opponent_token_average_x += x
            opponent_token_average_y += y

        #calculate the weight centers of tokens on both sides
        my_token_average_x /= my_token_number
        my_token_average_y /= my_token_number
        opponent_token_average_x /= opponent_token_number
        opponent_token_average_y /= opponent_token_number

        #calculate the distance of two weight centers
        distance = (my_token_average_x - opponent_token_average_x) * (my_token_average_x - opponent_token_average_x) \
                   + (my_token_average_y - opponent_token_average_y) * (my_token_average_y - opponent_token_average_y)

        score = 1 * my_token_number + 1 * (12 - opponent_token_number) - 0.01 * distance
        return score


    def print_board(self):
        my_tokens = self.my_tokens.copy()
        opponent_tokens = self.opponent_tokens.copy()
        board_tokens = my_tokens.copy()
        board_tokens.update(opponent_tokens)
        util.print_board(board_tokens)

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
        whiteInput = WHITE_INITIAL_SQUARES
        blackInput = BLACK_INITIAL_SQUARES
        white = dict()
        black = dict()
        for token in whiteInput:
            q, r = token
            white[(q, r)] = 1
        for token in blackInput:
            q, r = token
            black[(q, r)] = 1

        self.board = Board(self.color)

        self.init_my_tokens = white
        self.init_opponent_tokens = black
        # initialise state
        # White tokens go first
        self.state = State('white', self.board, self.init_my_tokens, self.init_opponent_tokens)

    def action(self):
        """
        This method is called at the beginning of each of your turns to request 
        a choice of action from your program.

        Based on the current state of the game, your player should select and
        return an allowed action to play on this turn. The action must be
        represented based on the spec's instructions for representing actions.
        """
        # TODO: Decide what action to take, and return it
        alpha = float("-inf")
        beta = float("inf")
        actions = self.state.get_legal_actions()
        for action in actions:
            successor_state = self.state.successor_state(action)
            current_eva_value = self.alphabeta(self.state, successor_state, 1, alpha, beta)
            if current_eva_value > alpha:
                # update evaluation
                alpha = current_eva_value
                # record the square the piece moves into
                best_action = action

        atype, aargs = best_action
        if atype == 'MOVE':
            p, q, r = aargs
            best_action = atype, p, q, r
            return best_action
        else:
            best_action = atype, aargs
            return best_action


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
        atype = action[0]
        if atype == 'MOVE':
            atype, p, q, r = action
            aargs = p, q, r
            action = atype, aargs
            self.state = self.state.successor_state(action)
        else:
            self.state = self.state.successor_state(action)

    def manhatten_distance(self, token, token2):
        x, y = token
        x2, y2 = token2
        distance = abs(x - x2) + abs(y - y2)
        return distance

    def alphabeta(self, last_state, current_state, current_depth, alpha, beta):
        # increase depth
        current_depth += 1

        #detect game over state
        if self.color == current_state.color:
            if len(current_state.opponent_tokens) == 0:
                return 999
            if len(current_state.my_tokens) == 0:
                return -999
        else:
            if len(current_state.opponent_tokens) == 0:
                return -999
            if len(current_state.my_tokens) == 0:
                return 999

        # record actions in a path
        moves = []

        # if max depth is reached
        if current_depth == MAX_DEPTH:
            # apply evaluation function
            return current_state.evaluation()

        if current_depth % 2 == 0:
            # min player's turn (enemy)
            legal_actions = current_state.get_legal_actions()

            for action in legal_actions:
                # alpha beta pruning
                if alpha < beta:
                    moves.append(action)
                    new_state = current_state.successor_state(action)
                    new_state = State(new_state.color, new_state.board, new_state.my_tokens,
                                      new_state.opponent_tokens)
                    current_evaluation_value = self.alphabeta(current_state, new_state, current_depth, alpha, beta)
                    # update beta
                    if beta > current_evaluation_value:
                        beta = current_evaluation_value
            return beta
        else:
            #max player's turn
            legal_actions = current_state.get_legal_actions()

            for action in legal_actions:

                # alpha beta pruning
                if alpha < beta:
                    moves.append(action)
                    new_state = current_state.successor_state(action)
                    new_state = State(new_state.color, new_state.board, new_state.my_tokens,
                                      new_state.opponent_tokens)
                    current_evaluation_value = self.alphabeta(current_state, new_state, current_depth, alpha, beta)
                    # update beta
                    if alpha < current_evaluation_value:
                        alpha = current_evaluation_value
            return alpha
