import pandas as pd
df = pd.read_csv('IRSet.csv')
print(df)
normalized_df_heght_colomn=(df-0)/(200-0)
normalized_df_value = (df-0)/(df.max()-0)
print(normalized_df_heght_colomn)
print(normalized_df_value)
newdf = df
newdf['Identifier'] = normalized_df_heght_colomn['Identifier']
newdf['value1'] = normalized_df_value['value1']
newdf['value2'] = normalized_df_value['value2']
newdf['value3'] = normalized_df_value['value3']
print(newdf)
newdf.to_csv('IRSet_Norm.csv', index=False)