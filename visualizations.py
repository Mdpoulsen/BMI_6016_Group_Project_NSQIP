#%%
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import ipywidgets as widget
from IPython.display import display


# %%
#Load data
path = '.\\Inpatient_Claims_markupcsv_code\\Inpatient_Claims_markup_Final_Full.csv'
data = pd.read_csv(path)

# %%
#Create a dataframe with only readmitted patients
data_readmit = data[data['counted_readmit'] == 1]
data_readmit

#%%
#get a list of all the DG ICD9 codes
allDGs = []

for i in range(5,14):
    allDGs.extend(data.iloc(axis=1)[i].tolist())

len(allDGs)

#%%
#count how many times each ICD9 code appears
DG_totals_dict = {}
for i in allDGs:
    if i not in DG_totals_dict:
        DG_totals_dict[i] = 1
    else:
        DG_totals_dict[i] += 1

#%%
#Create a new dataframe for the ICD9 codes and totals
DG_totals_df = pd.DataFrame(columns=['DG','Totals'])

for key, value in DG_totals_dict.items():
    record = {'DG': key,'Totals':value}
    DG_totals_df = DG_totals_df.append(record, ignore_index=True)

#%%
#Sort the dataframe so the top mentioned ICD9 codes are at the top
DG_totals_df = DG_totals_df.sort_values(by='Totals', ascending=False)

# %%
# Load the code descriptions
dg_desc_data = pd.read_excel(".\\CMS28_DESC_LONG_SHORT_DX.xls")
# %%
#Create a dictionary for the codes and descriptions
desc_dict = {}
for i in dg_desc_data.values:
    desc_dict[i[0]] = i[2]

# %%
#map the description to each code
DG_totals_df['desciption'] = DG_totals_df['DG'].map(desc_dict)
# %%
#plot the top 20 codes for readmitted patients
fig = DG_totals_df.head(20).plot.bar(x= 'desciption',y= 'Totals', title= "Most Common ICD9 Codes For Returning Patients", figsize = (7,5)).figure.savefig('.\\bar_with_description',bbox_inches='tight')


# %%
#Create a function for the interactive widget to plot the readmit, SSI, DVT, and reop for the given provider 
def plot_stats(df,x):
    sub_df = df[df['PRVDR_NUM'] == x]
    readmit_total = sub_df['counted_readmit'].sum()
    SSI_total = sub_df['counted_SSI'].sum()
    DVT_total = sub_df['counted_DVT'].sum()
    reop_total = sub_df['counted_reop'].sum()

    totals_df = pd.DataFrame({'lab':['readmit','SSI', 'DVT', 'reop'], 'val':[readmit_total, SSI_total, DVT_total, reop_total]})
    ax = totals_df.plot.bar(x='lab', y='val', rot=0)
    plt.show()


# %%
#Create interactive widget
widget.interact(plot_stats, df = widget.fixed(data), x='')
# %%
#plot the SSI, DVT, and reop totals across the dataset
readmit_total = data['counted_readmit'].sum()
SSI_total = data['counted_SSI'].sum()
DVT_total = data['counted_DVT'].sum()
reop_total = data['counted_reop'].sum()

totals_df = pd.DataFrame({'lab':['SSI', 'DVT', 'reop'], 'val':[SSI_total, DVT_total, reop_total]})

totals_df = pd.DataFrame({'lab':['SSI', 'DVT', 'reop'], 'val':[SSI_total, DVT_total, reop_total]})
ax = totals_df.plot.bar(x='lab', y='val', rot=0)
plt.savefig('.\\combinedStats')
plt.show()

# %%
