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

class End2EndModel(torch.nn.Module):
	def __init__(self, model1, model2):
		super(End2EndModel, self).__init__()
		self.first_model = model1#x to c
		self.sec_model = model2 #c to y

	def forward_stage2(self, c, x):
		return c,self.sec_model(c)

	def forward(self, x):
		c = self.first_model(x)
		return self.forward_stage2(c,x)

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

def XtoCtoY(n_features, n_concepts):

	layer_sizes=[n_features, 128, n_concepts] #dummy sidechannels
	x_to_c = MLP(layer_sizes, nn.ReLU, nn.Sigmoid)

	layer_sizes=[n_concepts, 64, 1]
	c_to_y = MLP(layer_sizes, nn.ReLU)

	return End2EndModel(x_to_c, c_to_y)


def createASSDatasetFromCSV(assDatasetPath):
	ass = pd.read_csv(assDatasetPath)
	feature_columns = [
		'Identifier',    'value1',    'value2',    'value3'
	]
	label_columns = [
	'g', 'l', 's', 'm', 'e', 'Goodness'
	]
	features = ass[feature_columns].values
	labels = ass[label_columns].values

	dataset = {}
	dataset['features'] = features
	dataset['labels'] = labels
	return dataset


def train(model, n_epoch,n_epoch_y, train_loader, lr,lr2, n_concepts, test_loader = None, criterion_c = torch.nn.CrossEntropyLoss(), criterion_y = torch.nn.MSELoss()):
	optimizerc = torch.optim.Adam(model.first_model.parameters(), lr=lr)
	optimizery = torch.optim.Adam(model.sec_model.parameters(), lr=lr2)
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
			
			optimizerc.zero_grad()

			outputs,y = model(inputs.reshape(inputs.size(0),4))

			loss = criterion_c(outputs,labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts])

			#  accumulate loss for metrics
			acc_train_loss = loss.clone().detach() + acc_train_loss

			dataset_counter_train = dataset_counter_train + outputs.size(0)

			torch_accuracy_total_temp = torch.eq(labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts],torch.round(outputs))
			torch_accuracy_total_temp = torch.sum(torch_accuracy_total_temp, dim=0)
			torch_accuracy_total = torch.add(torch_accuracy_total, torch_accuracy_total_temp)
						
			loss.backward()

			optimizerc.step()


		if test_loader is None:
			continue

		model.eval()
		with torch.no_grad():
			for j, data in enumerate(test_loader):
				inputs, labels = data

				outputs,y = model(inputs.reshape(inputs.size(0),4))

				loss = criterion_c(outputs,labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts])

				acc_test_loss = loss + acc_test_loss

				dataset_counter_test = dataset_counter_test + outputs.size(0)
				
				torch_accuracy_total_temp_test = torch.eq(labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts],torch.round(outputs))
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
		print(torch_y_accuracy_total/dataset_counter_train)
		accuracy_test_c = torch_accuracy_total_test/dataset_counter_test
		print(accuracy_test_c)
		print(torch_y_accuracy_total_test/dataset_counter_test)
		all_epoch.append(epoch)
		train_acc.append(accuracy_c)
		test_acc.append(accuracy_test_c)
		train_loss.append(acc_train_loss)
		test_loss.append(acc_test_loss)
	for epoch in range(n_epoch_y):
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
			
			optimizery.zero_grad()

			outputs,y = model(inputs.reshape(inputs.size(0),4))

			loss = criterion_y(y,labels.reshape(labels.size(0),n_concepts+1)[:,-1])

			#  accumulate loss for metrics
			acc_train_loss = loss.clone().detach() + acc_train_loss

			dataset_counter_train = dataset_counter_train + outputs.size(0)
			
			torch_accuracy_total_temp = torch.eq(labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts],torch.round(outputs))
			torch_accuracy_total_temp = torch.sum(torch_accuracy_total_temp, dim=0)
			torch_accuracy_total = torch.add(torch_accuracy_total, torch_accuracy_total_temp)
			torch_y_accuracy_total = torch_y_accuracy_total + criterion_y(y,labels.reshape(labels.size(0),n_concepts+1)[:,-1])
			
			loss.backward()

			optimizery.step()


		if test_loader is None:
			continue

		model.eval()
		with torch.no_grad():
			for j, data in enumerate(test_loader):
				inputs, labels = data

				outputs,y = model(inputs.reshape(inputs.size(0),4))

				loss = criterion_y(y,labels.reshape(labels.size(0),n_concepts+1)[:,-1])

				acc_test_loss = loss + acc_test_loss

				dataset_counter_test = dataset_counter_test + outputs.size(0)

				torch_accuracy_total_temp_test = torch.eq(labels.reshape(labels.size(0),n_concepts+1)[:,0:n_concepts],torch.round(outputs))
				torch_accuracy_total_temp_test = torch.sum(torch_accuracy_total_temp_test, dim=0)
				torch_accuracy_total_test = torch.add(torch_accuracy_total_test, torch_accuracy_total_temp_test)

				torch_y_accuracy_total_test = torch_y_accuracy_total_test + criterion_y(y,labels.reshape(labels.size(0),n_concepts+1)[:,-1])

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
		print(torch_y_accuracy_total/dataset_counter_train)
		accuracy_test_c = torch_accuracy_total_test/dataset_counter_test
		print(accuracy_test_c)
		print(torch_y_accuracy_total_test/dataset_counter_test)
		all_epoch.append(epoch)
		train_acc.append(accuracy_c)
		test_acc.append(accuracy_test_c)
		train_loss.append(acc_train_loss)
		test_loss.append(acc_test_loss)
	return all_epoch, train_acc, test_acc, train_loss, test_loss

BACKCipher = XtoCtoY(4,5)
ASSDataset = ASSDataset(createASSDatasetFromCSV('IRSet_Norm_Goodness.csv'))
trainSet, testSet, valSet = ASSDataset.get_splits()
trainSetLoader = DataLoader(TensorDataset(torch.tensor([[o[0]] for o in trainSet]), torch.tensor([[o[1]] for o in trainSet], dtype=torch.float32)), batch_size = 500, shuffle=True, generator = torch.Generator('cuda'))# batch max 12340
testSetLoader = DataLoader(TensorDataset(torch.tensor([[o[0]] for o in testSet]), torch.tensor([[o[1]] for o in testSet], dtype=torch.float32)), batch_size = 500, shuffle=False, generator = torch.Generator('cuda'))
epochs, train_acc, test_acc, train_loss, test_loss = train(BACKCipher, 5000,7500, trainSetLoader, 0.0007,0.0009, 5, testSetLoader)
torch.save(BACKCipher.state_dict(), '6_7500_back_model_save_bin.mdl')