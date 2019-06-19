from keras.models import Model, clone_model
from keras.layers import Input, Conv2D, Dense, Reshape, Dot
from keras.optimizers import SGD
import numpy as np

class Agent(object):

    def __init__(self,gamma=0.5, network='linear',lr=0.01):
        """
        Agent that plays the white pieces in capture chess
        Args:
            gamma: float
                Temporal discount factor
            network: str
                'linear' or 'conv'
            lr: float
                Learning rate, ideally around 0.1
        """
        self.gamma = gamma
        self.network = network
        self.lr = lr
        self.init_network()


    def init_network(self):
        """
        Initialize the network
        Returns:

        """
        if self.network == 'linear':
            self.init_linear_network()
        elif self.network == 'conv':
            self.init_conv_network()

    def fix_model(self):
        """
        The fixed model is the model used for bootstrapping
        Returns:
        """
        optimizer = SGD(lr=self.lr, momentum=0.0, decay=0.0, nesterov=False)
        self.fixed_model = clone_model(self.model)
        self.fixed_model.compile(optimizer=optimizer,loss='mse',metrics=['mae'])
        self.fixed_model.set_weights(self.model.get_weights())


    def init_linear_network(self):
        """
        Initialize a linear neural network
        Returns:

        """
        optimizer = SGD(lr=self.lr, momentum=0.0, decay=0.0, nesterov=False)
        input_layer = Input(shape=(8,8,8),name='board_layer')
        reshape_input = Reshape((512,))(input_layer)
        output_layer = Dense(4096)(reshape_input)
        self.model = Model(inputs=[input_layer],outputs=[output_layer])
        self.model.compile(optimizer=optimizer,loss='mse',metrics=['mae'])

    def init_conv_network(self):
        """
        Initialize a convolutional neural network
        Returns:

        """
        optimizer = SGD(lr=self.lr, momentum=0.0, decay=0.0, nesterov=False)
        input_layer = Input(shape=(8, 8, 8), name='board_layer')
        inter_layer_1 = Conv2D(1, (1, 1), data_format="channels_first")(input_layer)  # 1,8,8
        inter_layer_2 = Conv2D(1, (1, 1), data_format="channels_first")(input_layer)  # 1,8,8
        flat_1 = Reshape(target_shape=(1, 64))(inter_layer_1)
        flat_2 = Reshape(target_shape=(1, 64))(inter_layer_2)
        output_dot_layer = Dot(axes=1)([flat_1, flat_2])
        output_layer = Reshape(target_shape=(4096,))(output_dot_layer)
        self.model = Model(inputs=[input_layer], outputs=[output_layer])
        self.model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])

    def network_update(self,minibatch):
        """
        Update the Q-network using samples from the minibatch
        Args:
            minibatch: list
                The minibatch contains the states, moves, rewards and new states.

        Returns:
            td_errors: np.array
                array of temporal difference errors

        """

        # Prepare separate lists
        states, moves, rewards, new_states = [],[],[],[]
        td_errors = []
        episode_ends = []
        for sample in minibatch:
            states.append(sample[0])
            moves.append(sample[1])
            rewards.append(sample[2])
            new_states.append(sample[3])

            # Episode end detection
            if np.array_equal(sample[3], sample[3] * 0):
                episode_ends.append(0)
            else:
                episode_ends.append(1)

        # The Q target
        q_target = np.array(rewards) + np.array(episode_ends) * self.gamma * np.max(self.fixed_model.predict(np.stack(new_states,axis=0)),axis=1)  # Max value of actions in new state

        # The Q value for the remaining actions
        q_state = self.model.predict(np.stack(states,axis=0))  # batch x 64 x 64

        # Combine the Q target with the other Q values.
        q_state = np.reshape(q_state,(len(minibatch),64,64))
        for idx, move in enumerate(moves):
            td_errors.append(q_state[idx,move[0],move[1]] - q_target[idx])
            q_state[idx,move[0],move[1]] = q_target[idx]
        q_state = np.reshape(q_state,(len(minibatch),4096))

        # Perform a step of minibatch Gradient Descent.
        self.model.fit(x=np.stack(states,axis=0),y=q_state,epochs=1,verbose=0)

        return td_errors

    def get_action_values(self,state):
        """
        Get action values of a state
        Args:
            state: np.ndarray with shape (8,8,8)
                layer_board representation

        Returns:
            action values

        """
        return self.fixed_model.predict(state)
















