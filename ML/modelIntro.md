The ML model consists of two parts - the Concept Bottleneck Model for IR TOF predictions and the Multi Layer Perceptron for flex sensor predictions.

Concept Bottleneck Models (CBMs) have been posed as an alternative to deep neural networks in many prediction tasks. These models map raw inputs to high-level concepts, and then concepts to targets. The idea is to incorporate high-level concepts into the learning procedure to enable interpretability, intervenability and predictability. 

The type of CBM chosen for this task is a hard CBM trained in a sequential manner. The loss is calculated as the equation in loss.png in this directory.

The CBM takes in 3 inputs from IR TOF sensors and 1 input of height, predicts a posture score varying around 0-100 (2sigma). It is also trained to provide reasons why the model predicts that score by providing a list of one-hot encoding indicating if ['Good', 'Lean Forward', 'Lying too low', 'Medium', 'Empty'] exists.

The Multi Layer Perceptron takes in input of 2 flex sensor readings and returns a posture score between 0 and 1.

