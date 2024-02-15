import torch
import torch.nn as nn

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

	layer_sizes=[n_concepts, 1]
	c_to_y = MLP(layer_sizes, nn.ReLU)

	return End2EndModel(x_to_c, c_to_y)

#model initialization
def Flex_Model_Initialization(model_dir):
   model = MLP([2, 128, 128, 1], nn.ReLU, nn.Sigmoid)
   model.load_state_dict(torch.load(model_dir)) #directory "model_save_bin.mdl"
   return model
def IR_model_initialization(IR_Model_Dir):
	BACKCipher = XtoCtoY(4,5)
	BACKCipher.load_state_dict(torch.load(IR_Model_Dir))
	return BACKCipher
ASSCipher = Flex_Model_Initialization('model_save_bin_cpu.mdl')
BACKCipher = IR_model_initialization('5_7500_back_model_save_bin.mdl')

def normalize_IR(ir_raw):
	return ir_raw/8190.0
def normalize_Height(height_raw):
	return height_raw/200.0
def normalize_Flex(flex_reading1, flex_reading2):
	return flex_reading1/16783.0-1.0, flex_reading2/14581.0-1.0
def set_max_to_one(lst):
	if not lst:
		return []

	max_value = max(lst)
	max_index = max(range(len(lst)), key=lst.__getitem__)

	result = [0.0] * len(lst)
	result[max_index] = 1.0

	return result

def IR_Model_Predict(model, height, IR_raw): 
	### takes in the model, height(float) and raw data from ir(list of float),
	### returns a tuple of Posture Score (float) and Identified Type (list of float, either 1 or 0, 1 indicating which type identified)
	### types in order of typelist = ['Good', 'Lean Forward', 'Lying too low', 'Medium', 'Empty']

	data = [height]+IR_raw
	Type, PostureScore = model(torch.tensor([normalize_Height(data[0]),normalize_IR(data[1]),normalize_IR(data[2]),normalize_IR(data[3])]))
	Type = Type.tolist()
	PostureScore = PostureScore.item()
	Type = set_max_to_one(Type)
	return PostureScore,Type

def Flex_Model_Predict(model,sampler_buffer):
	### takes in the model, and sampler buffer. It extracts left and right flex sensor readings
	### returns 0.0 to 1.0 on whether the posture is good (1.0 good, 0.0 bad)

	left = 0
	right = 0
	counter = 0
	for first,second in zip(sampler_buffer[::8], sampler_buffer[1::8]):
		counter = counter + 1
		normalized_first, normalized_second = normalize_Flex(first, second)
		left = left + normalized_first
		right = right + normalized_second
	left = left / counter
	right = right / counter
	logits = model(torch.tensor([left,right]).type(torch.float32))
	return logits

print(IR_Model_Predict(BACKCipher, 188.0, [147.0, 34.0, 22.0]))
print(Flex_Model_Predict(ASSCipher,[15191,14053]))