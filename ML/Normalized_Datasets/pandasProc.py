import pandas as pd
df = pd.read_csv('IRSet_Norm.csv')
newdf = df
newdf 
newdf.to_csv('IRSet_Norm.csv', index=False)