import torch
import torch.nn as nn
import time

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

model = MLP([2, 128, 128, 1], nn.ReLU, nn.Sigmoid)
model.load_state_dict(torch.load("model_save_bin_cpu.mdl"))

adcdata = [16000,14000,32767,32767]
distancedata = [60,50,60]
sampler_buffer = adcdata + distancedata + [-1] +adcdata + distancedata + [-1] +adcdata + distancedata + [-1]
print(sampler_buffer)

left = 0
right = 0
counter = 0
for first,second in zip(sampler_buffer[::8], sampler_buffer[1::8]):
	counter = counter + 1
	left = left + first
	right = right + second
left = left / counter
right = right / counter
print(left)
print(right)

logits = model(torch.tensor([14581,15863]).type(torch.float32))

print(logits.item())