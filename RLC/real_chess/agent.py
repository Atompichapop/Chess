from keras.layers import Input, Dense, Flatten, Concatenate, Conv2D, Dropout
from keras.losses import mean_squared_error
from keras.models import Model, clone_model
from keras.optimizers import Adam
import numpy as np


class RandomAgent(object):

    def __init__(self):
        pass

    def predict(self,board_layer):
        return np.random.randint(-5,5)/5

    def select_move(self,board):
        moves = [x for x in board.generate_legal_moves()]
        return np.random.choice(moves)

class Agent(object):

    def __init__(self):
        self.model = Model()
        self.init_network()
        self.has_won = False
        self.has_lost = False

    def fix_model(self):
        """
        The fixed model is the model used for bootstrapping
        Returns:
        """
        optimizer = Adam()
        self.fixed_model = clone_model(self.model)
        self.fixed_model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        self.fixed_model.set_weights(self.model.get_weights())

    def init_network(self):
        optimizer = Adam()
        layer_state = Input(shape=(8,8,8),name='state')

        openfile = Conv2D(3,(8,1),padding='valid',activation='relu',name='fileconv')(layer_state)  # 3,8,1
        openrank = Conv2D(3,(1,8),padding='valid',activation='relu',name='rankconv')(layer_state)  # 3,1,8
        quarters = Conv2D(3,(4,4),padding='valid',activation='relu',name='quarterconv',strides=(4,4))(layer_state)  # 3,2,2
        large = Conv2D(8,(6,6),padding='valid',activation='relu',name='largeconv')(layer_state)  # 8,2,2

        board1 = Conv2D(16, (3, 3), padding='valid', activation='relu', name='board1')(layer_state)   # 16,6,6
        board2 = Conv2D(20, (3, 3), padding='valid', activation='relu', name='board2')(board1)   # 20,4,4
        board3 = Conv2D(24, (3, 3), padding='valid',activation='relu',name='board3')(board2)  # 24,2,2

        flat_file = Flatten()(openfile)
        flat_rank = Flatten()(openrank)
        flat_quarters = Flatten()(quarters)
        flat_large = Flatten()(large)

        flat_board = Flatten()(board1)
        flat_board3 = Flatten()(board3)

        dense1 = Concatenate(name='dense_bass')([flat_file,flat_rank,flat_quarters,flat_large,flat_board,flat_board3])
        dropout1 = Dropout(rate=0.1)(dense1)
        dense2 = Dense(128)(dropout1)
        dense3 = Dense(64)(dense2)
        dropout3 = Dropout(rate=0.1)(dense3,training=True)
        dense4 = Dense(32)(dropout3)
        dropout4 = Dropout(rate=0.1)(dense4,training=True)

        value_head = Dense(1,activation='tanh')(dropout4)
        self.model = Model(inputs=layer_state,
                           outputs=[value_head])
        self.model.compile(optimizer=optimizer,
                           loss=[mean_squared_error]
                           )

    def predict_distribution(self,states,batch_size=256):
        """
        :param states: list of distinct states
        :param n:  each state is predicted n times
        :return:
        """
        predictions_per_state = int(batch_size / len(states))
        state_batch = []
        for state in states:
            state_batch = state_batch + [state for x in range(predictions_per_state)]

        state_batch = np.stack(state_batch,axis=0)
        predictions = self.model.predict(state_batch)
        predictions = predictions.reshape(len(states),predictions_per_state)
        mean_pred = np.mean(predictions,axis=1)
        std_pred = np.std(predictions,axis=1)
        upper_bound = mean_pred + 2*std_pred

        return mean_pred, std_pred, upper_bound

    def predict(self,board_layer):
        return self.model.predict(board_layer)

    def network_update(self, minibatch,gamma=0.9):
        """
        Update the SARSA-network using samples from the minibatch
        Args:
            minibatch: list
                The minibatch contains the states, moves, rewards and new states.

        Returns:
            td_errors: np.array
                array of temporal difference errors

        """

        # Prepare separate lists
        states, rewards, new_states = [], [], []
        td_errors = []
        episode_ends = []
        for sample in minibatch:
            states.append(sample[0])
            rewards.append(sample[1])
            new_states.append(sample[2])

            # Episode end detection
            if sample[1] != 0:
                episode_ends.append(0)
                if sample[1] < 0:
                    self.has_lost = True
                else:
                    self.has_won = True
            else:
                episode_ends.append(1)

        # The V target
        suc_state_value = self.fixed_model.predict(np.stack(new_states, axis=0))
        V_target = np.array(rewards) + np.array(episode_ends) * gamma * np.squeeze(suc_state_value)
        V_target = np.expand_dims(V_target,axis=-1)

        # The Q value for the remaining actions
        V_state = self.model.predict(np.stack(states, axis=0))  # the expected future returns
        
        td_errors = V_target - V_state

        # Perform a step of minibatch Gradient Descent.
        self.model.fit(x=np.stack(states, axis=0), y=np.stack(V_target,axis=0), epochs=1, verbose=0)

        return td_errors


















