# Import necessary libraries
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
from torch.autograd import Variable

# -------------------------------
# 1. Load the MovieLens 1M dataset
# -------------------------------

# Load users, movies, and ratings data
users = pd.read_csv('ml-1m/users.dat', sep='::', header=None, engine='python', encoding='latin-1')
films = pd.read_csv('ml-1m/movies.dat', sep='::', header=None, engine='python', encoding='latin-1')
ratings = pd.read_csv('ml-1m/ratings.dat', sep='::', header=None, engine='python', encoding='latin-1')

# Load and convert training/test sets
training_set = pd.read_csv('ml-100k/u1.base', delimiter='\t')
test_set = pd.read_csv('ml-100k/u1.test', delimiter='\t')

training_set = np.array(training_set, dtype='int')
test_set = np.array(test_set, dtype='int')

# -------------------------------
# 2. Prepare the dataset
# -------------------------------

# Get number of unique users and movies
users_number = int(max(max(training_set[:, 0]), max(test_set[:, 0])))
films_number = int(max(max(training_set[:, 1]), max(test_set[:, 1])))

# Convert ratings data into a matrix
def convert(data):
    new_list = []
    for user_id in range(1, users_number + 1):
        ratings_id = data[:, 2][data[:, 0] == user_id]
        films_id = data[:, 1][data[:, 0] == user_id]
        ratings = np.zeros(films_number)
        ratings[films_id - 1] = ratings_id
        new_list.append(list(ratings))
    return new_list

training_set = torch.FloatTensor(convert(training_set))
test_set = torch.FloatTensor(convert(test_set))

# Convert ratings to binary values
training_set[training_set == 0] = -1
training_set[training_set == 1] = 0
training_set[training_set == 2] = 0
training_set[training_set >= 3] = 1

test_set[test_set == 0] = -1
test_set[test_set == 1] = 0
test_set[test_set == 2] = 0
test_set[test_set >= 3] = 1

# -------------------------------
# 3. Build the Restricted Boltzmann Machine (RBM)
# -------------------------------

class RBM():
    def __init__(self, visible_nodes, hidden_nodes):
        self.Weights = torch.randn(hidden_nodes, visible_nodes)
        self.a = torch.randn(1, hidden_nodes)
        self.b = torch.randn(1, visible_nodes)

    def sample_h(self, x):
        wx = torch.mm(x, self.Weights.t())
        activation = wx + self.a.expand_as(wx)
        prob_h_given_v = torch.sigmoid(activation)
        return prob_h_given_v, torch.bernoulli(prob_h_given_v)

    def sample_v(self, y):
        wy = torch.mm(y, self.Weights)
        activation = wy + self.b.expand_as(wy)
        prob_v_given_h = torch.sigmoid(activation)
        return prob_v_given_h, torch.bernoulli(prob_v_given_h)

    def train(self, v0, vk, ph0, phk):
        self.Weights += torch.mm(ph0.t(), v0) - torch.mm(phk.t(), vk)
        self.b += torch.sum((v0 - vk), 0)
        self.a += torch.sum((ph0 - phk), 0)

# Initialize RBM parameters
visible_nodes = len(training_set[0])
hidden_nodes = 90
batch_size = 85
rbm = RBM(visible_nodes, hidden_nodes)

# -------------------------------
# 4. Train the RBM
# -------------------------------

epoch_numbers = 15

for epoch in range(1, epoch_numbers + 1):
    train_loss = 0
    s = 0.0
    for user_id in range(0, users_number - batch_size, batch_size):
        v0 = training_set[user_id:user_id + batch_size]
        vk = training_set[user_id:user_id + batch_size]
        ph0, _ = rbm.sample_h(v0)

        for k in range(10):
            _, hk = rbm.sample_h(vk)
            _, vk = rbm.sample_v(hk)
            vk[v0 < 0] = v0[v0 < 0]

        phk, _ = rbm.sample_h(vk)
        rbm.train(v0, vk, ph0, phk)
        train_loss += torch.mean(torch.abs(v0[v0 >= 0] - vk[v0 >= 0]))
        s += 1.0

    print(f'Epoch: {epoch} Loss: {train_loss / s:.4f}')

# -------------------------------
# 5. Test the RBM
# -------------------------------

test_loss = 0
s = 0.0

for user_id in range(users_number):
    v = training_set[user_id:user_id + 1]
    vt = test_set[user_id:user_id + 1]
    if len(vt[vt >= 0]) > 0:
        _, h = rbm.sample_h(v)
        _, v_reconstructed = rbm.sample_v(h)
        test_loss += torch.mean(torch.abs(vt[vt >= 0] - v_reconstructed[vt >= 0]))
        s += 1.0

print(f'Test Loss: {test_loss / s:.4f}')
