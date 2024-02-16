import torch
import torch.nn as nn
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from torch.utils.data import random_split
from torch.utils.data import TensorDataset
import math
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.pyplot import cm
import numpy as np
from datetime import datetime
import time
import pandas as pd
import scipy

torch.set_default_tensor_type('torch.cuda.FloatTensor')
# setting device on GPU if available, else CPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print('Using device:', device)
print()
torch.set_printoptions(precision=16, sci_mode=False)
color_plt = cm.rainbow(np.linspace(0, 1, 20))
mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color = mpl.cm.tab20(range(20))) 
#https://stackoverflow.com/questions/9397944/how-to-set-the-default-color-cycle-for-all-subplots-with-matplotlib
#Additional Info when using cuda
if device.type == 'cuda':
	print(torch.cuda.get_device_name(0))
	print('Memory Usage:')
	print('Allocated:', round(torch.cuda.memory_allocated(0)/1024**3,1), 'GB')
	print('Cached:   ', round(torch.cuda.memory_reserved(0)/1024**3,1), 'GB')

def softmax(z):
	assert len(z.shape) == 2
	s = np.max(z, axis=1)
	s = s[:, np.newaxis] # necessary step to do broadcasting
	e_x = np.exp(z - s)
	div = np.sum(e_x, axis=1)
	div = div[:, np.newaxis] # dito
	return e_x / div

class ASSDataset(Dataset):
	def __init__(self, generated):
		self.features = generated['features'][:]
		self.labelAndConcepts = generated['labels'][:]
		self.features = self.features.astype('float32')
		self.labelAndConcepts = self.labelAndConcepts.astype('float32')
		#self.concepts = self.concept   s.reshape((len(self.concepts), 1))
	
	def __len__(self):
		return len(self.features)
	
	def __getitem__(self, idx):
		return [self.features[idx], self.labelAndConcepts[idx]]
		#return [self.features_continuous[idx], self.concepts[idx]]

	def get_splits(self, n_test=0.15, n_val = 0.15):
		# determine sizes
		test_size = round(n_test * len(self.features))
		train_size = len(self.features) - 2*test_size
		# calculate the split
		train, test,val = random_split(self, [train_size, test_size, test_size], generator = torch.Generator('cuda'))
		# train, rest = random_split(self, [train_size, 2*test_size])
		# test,val = random_split(rest, [test_size, test_size])
		return train,test,val

class MLP(nn.Module):
	def __init__(self, layer_sizes, activation=nn.ReLU, final_activation=None, lr=0.001):
		super(MLP, self).__init__()
		
		layers = []
		for i in range(len(layer_sizes) - 1):
			layers.extend([
				nn.Linear(layer_sizes[i], layer_sizes[i+1]),
				activation(),
			])
		
		# Pop off the last activation
		layers.pop()
		if final_activation:
			layers.append(final_activation())

		self.model = nn.Sequential(*layers)
		#self.device = device

	def forward(self, x):
		return self.model.forward(x)

def createASSDatasetFromCSV(assDatasetPath):
	ass = pd.read_csv(assDatasetPath)
	feature_columns = [
		'Identifier',    'value1',    'value2',    'value3'
	]
	label_columns = [
	'g', 'l', 's', 'm', 'e'
	]
	features = ass[feature_columns].values
	labels = ass[label_columns].values

	dataset = {}
	dataset['features'] = features
	dataset['labels'] = labels
	return dataset


def train(model, n_epoch, train_loader, lr, n_concepts, test_loader = None, criterion = torch.nn.CrossEntropyLoss()):
	optimizer = torch.optim.Adam(model.parameters(), lr=lr)
	all_epoch = []
	train_acc = []
	test_acc = []
	train_loss = []
	test_loss = []
	for epoch in range(n_epoch):
		#  accuracy calculation dummy variables
		dataset_counter_train = 0
		dataset_counter_test = 0
		
		#  metric buffers 
		acc_test_loss = 0
		acc_train_loss = 0

		torch_accuracy_total = torch.zeros(n_concepts).to(device)
		torch_accuracy_total_test = torch.zeros(n_concepts).to(device)
		torch_y_accuracy_total = 0
		torch_y_accuracy_total_test = 0


		for i,data in enumerate(train_loader):

			inputs, labels = data
			inputs = inputs.float()
			labels = labels.float()
			
			optimizer.zero_grad()

			outputs = model(inputs.reshape(inputs.size(0),4))

			loss = criterion(outputs,labels.reshape(labels.size(0),n_concepts))

			#  accumulate loss for metrics
			acc_train_loss = loss.clone().detach() + acc_train_loss

			dataset_counter_train = dataset_counter_train + outputs.size(0)

			torch_accuracy_total_temp = torch.eq(labels.reshape(labels.size(0),n_concepts),torch.round(outputs))
			torch_accuracy_total_temp = torch.sum(torch_accuracy_total_temp, dim=0)
			torch_accuracy_total = torch.add(torch_accuracy_total, torch_accuracy_total_temp)

			loss.backward()

			optimizer.step()


		if test_loader is None:
			continue

		model.eval()
		with torch.no_grad():
			for j, data in enumerate(test_loader):
				inputs, labels = data

				outputs = model(inputs.reshape(inputs.size(0),4))

				loss = criterion(outputs,labels.reshape(labels.size(0),n_concepts))

				acc_test_loss = loss + acc_test_loss

				dataset_counter_test = dataset_counter_test + outputs.size(0)
				
				torch_accuracy_total_temp_test = torch.eq(labels.reshape(labels.size(0),n_concepts),torch.round(outputs))
				torch_accuracy_total_temp_test = torch.sum(torch_accuracy_total_temp_test, dim=0)
				torch_accuracy_total_test = torch.add(torch_accuracy_total_test, torch_accuracy_total_temp_test)


		model.train()

		# #  print training status
		print("=======================")
		print(epoch)
		print("==Loss==")
		print(acc_train_loss)
		print(acc_test_loss)
		print("==Accuracy==")
		accuracy_c = torch_accuracy_total/dataset_counter_train
		print(accuracy_c)
		accuracy_test_c = torch_accuracy_total_test/dataset_counter_test
		print(accuracy_test_c)
		all_epoch.append(epoch)
		train_acc.append(accuracy_c)
		test_acc.append(accuracy_test_c)
		train_loss.append(acc_train_loss)
		test_loss.append(acc_test_loss)
	return all_epoch, train_acc, test_acc, train_loss, test_loss

BACKCipher = MLP([4, 128, 128, 5], nn.ReLU, nn.Sigmoid)
ASSDataset = ASSDataset(createASSDatasetFromCSV('IRSet_Norm.csv'))
trainSet, testSet, valSet = ASSDataset.get_splits()
trainSetLoader = DataLoader(TensorDataset(torch.tensor([[o[0]] for o in trainSet]), torch.tensor([[o[1]] for o in trainSet], dtype=torch.float32)), batch_size = 500, shuffle=True, generator = torch.Generator('cuda'))# batch max 12340
testSetLoader = DataLoader(TensorDataset(torch.tensor([[o[0]] for o in testSet]), torch.tensor([[o[1]] for o in testSet], dtype=torch.float32)), batch_size = 500, shuffle=False, generator = torch.Generator('cuda'))
epochs, train_acc, test_acc, train_loss, test_loss = train(BACKCipher, 7500, trainSetLoader, 0.0007, 5, testSetLoader)
torch.save(BACKCipher.state_dict(), '7500_back_model_save_bin.mdl')
epochs = torch.tensor(epochs, device = 'cpu')
train_loss = torch.tensor(train_loss, device = 'cpu')
test_loss = torch.tensor(test_loss, device = 'cpu')
train_acc = torch.tensor(torch.stack((train_acc)), device = 'cpu')
test_acc = torch.tensor(torch.stack((test_acc)), device = 'cpu')

plt.plot(epochs, train_loss, '-')
plt.xlabel('# Epoch')
plt.ylabel('Accumulated Loss over Train Dataset per Epoch')
plt.title("Train Loss")

plt.savefig('7500_IR_train_loss.jpg')
plt.cla()

plt.plot(epochs, train_acc, '-')
plt.xlabel('# Epoch')
plt.ylabel('Accuracy over Train Dataset per Epoch')
plt.title("Train Accuracy")
plt.savefig('7500_IR_train_accuracy.jpg')

plt.cla()

plt.plot(epochs, test_loss, '-')
plt.xlabel('# Epoch')
plt.ylabel('Accuracy over Train Dataset per Epoch')
plt.title("Test Loss")
plt.savefig('7500_IR_test_loss.jpg')

plt.cla()

plt.plot(epochs, test_acc, '-')
plt.xlabel('# Epoch')
plt.ylabel('Accuracy over Train Dataset per Epoch')
plt.title("Test Accuracy")
plt.savefig('7500_IR_test_Accuracy.jpg')

plt.cla()

plt.plot(epochs, train_loss, '-')
plt.plot(epochs, test_loss, '-')
plt.xlabel('# Epoch')
plt.ylabel('Accuracy over Train Dataset per Epoch')
plt.title("Loss")
plt.savefig('7500_IR_combined_loss.jpg')
plt.legend(['train','test'])

plt.cla()